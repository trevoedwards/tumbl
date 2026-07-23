<?php
/**
 * Remap WordPress post IDs that exceed JavaScript Number.MAX_SAFE_INTEGER.
 *
 * Tumblr snowflake IDs imported as wp:post_id break Gutenberg ("item doesn't exist")
 * and can inflate wp_posts AUTO_INCREMENT. This script assigns safe sequential IDs
 * while preserving slugs (tumblr-{id}) and storing the original ID in _tumblr_post_id.
 *
 * BACK UP YOUR DATABASE BEFORE RUNNING WITH --apply.
 *
 * Usage (WP-CLI, from WordPress root):
 *   wp eval-file /path/to/remap_wordpress_unsafe_ids.php -- --dry-run
 *   wp eval-file /path/to/remap_wordpress_unsafe_ids.php -- --apply
 *
 * Or as a one-shot mu-plugin:
 *   1. Copy to wp-content/mu-plugins/remap_wordpress_unsafe_ids.php
 *   2. Visit /wp-admin/?tumbl_remap_unsafe_ids=1&dry_run=1 (preview)
 *   3. Visit /wp-admin/?tumbl_remap_unsafe_ids=1&apply=1 (run once)
 *   4. Delete the file
 */

if (!defined('ABSPATH')) {
    // WP-CLI eval-file: bootstrap WordPress when run standalone.
    $wp_load = getenv('TUMBL_WP_LOAD') ?: null;
    if ($wp_load && is_readable($wp_load)) {
        require_once $wp_load;
    } else {
        foreach ([__DIR__ . '/../../../wp-load.php', __DIR__ . '/../../wp-load.php', __DIR__ . '/../wp-load.php'] as $candidate) {
            if (is_readable($candidate)) {
                require_once $candidate;
                break;
            }
        }
    }
}

if (!defined('ABSPATH')) {
    fwrite(STDERR, "Could not load WordPress. Set TUMBL_WP_LOAD=/path/to/wp-load.php\n");
    exit(1);
}

/**
 * JavaScript Number.MAX_SAFE_INTEGER — Gutenberg cannot edit posts above this.
 */
const TUMBL_JS_MAX_SAFE_INTEGER = 9007199254740991;

/**
 * @return array{dry_run: bool, apply: bool}
 */
function tumbl_remap_parse_args(): array
{
    $dry_run = false;
    $apply = false;

    if (defined('WP_CLI') && WP_CLI) {
        global $argv;
        $dry_run = in_array('--dry-run', $argv, true);
        $apply = in_array('--apply', $argv, true);
    } elseif (is_admin() && current_user_can('manage_options')) {
        $dry_run = isset($_GET['dry_run']);
        $apply = isset($_GET['apply']);
    }

    if (!$dry_run && !$apply) {
        $dry_run = true;
    }

    return ['dry_run' => $dry_run, 'apply' => !$dry_run && $apply];
}

/**
 * @return array<int, int> old_id => new_id
 */
function tumbl_remap_build_mapping(wpdb $wpdb): array
{
    $table = $wpdb->posts;
    $max_safe = (string) TUMBL_JS_MAX_SAFE_INTEGER;

    $unsafe_ids = $wpdb->get_col(
        $wpdb->prepare(
            "SELECT ID FROM {$table} WHERE ID > %d ORDER BY ID ASC",
            $max_safe
        )
    );

    if (!$unsafe_ids) {
        return [];
    }

    $next_id = (int) $wpdb->get_var(
        $wpdb->prepare(
            "SELECT MAX(ID) FROM {$table} WHERE ID <= %d",
            $max_safe
        )
    );
    $next_id = max(1, $next_id + 1);

    $mapping = [];
    foreach ($unsafe_ids as $old_id) {
        $old_id = (int) $old_id;
        while ($wpdb->get_var($wpdb->prepare("SELECT ID FROM {$table} WHERE ID = %d", $next_id))) {
            $next_id++;
        }
        $mapping[$old_id] = $next_id;
        $next_id++;
    }

    return $mapping;
}

/**
 * @param array<int, int> $mapping
 */
function tumbl_remap_ensure_tumblr_meta(wpdb $wpdb, int $post_id, int $old_id): void
{
    $existing = $wpdb->get_var(
        $wpdb->prepare(
            "SELECT meta_id FROM {$wpdb->postmeta} WHERE post_id = %d AND meta_key = %s LIMIT 1",
            $post_id,
            '_tumblr_post_id'
        )
    );
    if ($existing) {
        return;
    }

    $slug = $wpdb->get_var(
        $wpdb->prepare("SELECT post_name FROM {$wpdb->posts} WHERE ID = %d", $post_id)
    );
    $tumblr_id = (string) $old_id;
    if (is_string($slug) && preg_match('/^(?:tumblr|post)-(\d+)$/', $slug, $matches)) {
        $tumblr_id = $matches[1];
    }

    $wpdb->insert(
        $wpdb->postmeta,
        [
            'post_id' => $post_id,
            'meta_key' => '_tumblr_post_id',
            'meta_value' => $tumblr_id,
        ],
        ['%d', '%s', '%s']
    );
}

/**
 * @param array<int, int> $mapping
 * @return array{remapped: int, auto_increment: int}
 */
function tumbl_remap_apply(wpdb $wpdb, array $mapping, bool $dry_run): array
{
    if (!$mapping) {
        return ['remapped' => 0, 'auto_increment' => 0];
    }

    $remapped = 0;
    foreach ($mapping as $old_id => $new_id) {
        if ($dry_run) {
            $slug = $wpdb->get_var(
                $wpdb->prepare("SELECT post_name FROM {$wpdb->posts} WHERE ID = %d", $old_id)
            );
            $type = $wpdb->get_var(
                $wpdb->prepare("SELECT post_type FROM {$wpdb->posts} WHERE ID = %d", $old_id)
            );
            echo "[dry-run] {$old_id} -> {$new_id} ({$type}, slug={$slug})\n";
            $remapped++;
            continue;
        }

        // Update references before changing the primary key.
        $wpdb->query(
            $wpdb->prepare(
                "UPDATE {$wpdb->posts} SET post_parent = %d WHERE post_parent = %d",
                $new_id,
                $old_id
            )
        );
        $wpdb->query(
            $wpdb->prepare(
                "UPDATE {$wpdb->postmeta} SET post_id = %d WHERE post_id = %d",
                $new_id,
                $old_id
            )
        );
        $wpdb->query(
            $wpdb->prepare(
                "UPDATE {$wpdb->term_relationships} SET object_id = %d WHERE object_id = %d",
                $new_id,
                $old_id
            )
        );
        $wpdb->query(
            $wpdb->prepare(
                "UPDATE {$wpdb->comments} SET comment_post_ID = %d WHERE comment_post_ID = %d",
                $new_id,
                $old_id
            )
        );
        $wpdb->update(
            $wpdb->posts,
            ['ID' => $new_id],
            ['ID' => $old_id],
            ['%d'],
            ['%d']
        );

        tumbl_remap_ensure_tumblr_meta($wpdb, $new_id, $old_id);
        echo "Remapped {$old_id} -> {$new_id}\n";
        $remapped++;
    }

    $auto_increment = 0;
    if (!$dry_run) {
        $max_id = (int) $wpdb->get_var("SELECT MAX(ID) FROM {$wpdb->posts}");
        $auto_increment = $max_id + 1;
        $wpdb->query("ALTER TABLE {$wpdb->posts} AUTO_INCREMENT = {$auto_increment}");
        echo "Set wp_posts AUTO_INCREMENT to {$auto_increment}\n";
    }

    return ['remapped' => $remapped, 'auto_increment' => $auto_increment];
}

function tumbl_remap_run(): void
{
    global $wpdb;

    $args = tumbl_remap_parse_args();
    $mapping = tumbl_remap_build_mapping($wpdb);

    echo 'Unsafe posts (ID > ' . TUMBL_JS_MAX_SAFE_INTEGER . '): ' . count($mapping) . "\n";
    if (!$mapping) {
        echo "Nothing to remap.\n";
        return;
    }

    if ($args['dry_run']) {
        echo "DRY RUN — no database changes.\n";
    } elseif ($args['apply']) {
        echo "APPLYING changes — ensure you have a database backup.\n";
    }

    $result = tumbl_remap_apply($wpdb, $mapping, $args['dry_run']);
    echo "Done. remapped={$result['remapped']}\n";
}

// WP-CLI or direct CLI include.
if (php_sapi_name() === 'cli' || (defined('WP_CLI') && WP_CLI)) {
    tumbl_remap_run();
}

// mu-plugin admin trigger (one-shot).
add_action('admin_init', static function (): void {
    if (!isset($_GET['tumbl_remap_unsafe_ids']) || !current_user_can('manage_options')) {
        return;
    }
    if (!isset($_GET['_wpnonce']) || !wp_verify_nonce(sanitize_text_field(wp_unslash($_GET['_wpnonce'])), 'tumbl_remap_unsafe_ids')) {
        wp_die('Invalid nonce. Append &_wpnonce=' . wp_create_nonce('tumbl_remap_unsafe_ids'));
    }
    header('Content-Type: text/plain; charset=utf-8');
    tumbl_remap_run();
    exit;
});
