(function () {
    "use strict";

    var STORAGE_KEY = "tumbl.settings";
    var DEFAULT_BG_LIGHT = "#f0f0f0";
    var DEFAULT_BG_DARK = "#001935";
    var HEX_COLOR_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
    var DEFAULTS = {
        infiniteScroll: false,
        darkMode: false,
        backgroundColor: "",
        backgroundImage: "",
        blogTitle: "",
    };

    function getDefaultBlogTitle() {
        var body = document.body;
        if (body && body.dataset.defaultBlogTitle) {
            return body.dataset.defaultBlogTitle;
        }
        var headerLink = document.querySelector(".blog-title");
        if (headerLink && headerLink.dataset.defaultTitle) {
            return headerLink.dataset.defaultTitle;
        }
        return "MyBlog";
    }

    function getDefaultBackgroundImage() {
        var body = document.body;
        return body && body.dataset.defaultBackgroundImage
            ? body.dataset.defaultBackgroundImage
            : "";
    }

    function getDisplayBlogTitle(settings) {
        var customTitle = (settings.blogTitle || "").trim();
        return customTitle || getDefaultBlogTitle();
    }

    function normalizeHexColor(value) {
        var trimmed = (value || "").trim();
        if (!trimmed) {
            return "";
        }
        if (!trimmed.startsWith("#")) {
            trimmed = "#" + trimmed;
        }
        if (!HEX_COLOR_RE.test(trimmed)) {
            return "";
        }
        if (trimmed.length === 4) {
            return (
                "#" +
                trimmed[1] + trimmed[1] +
                trimmed[2] + trimmed[2] +
                trimmed[3] + trimmed[3]
            ).toLowerCase();
        }
        return trimmed.toLowerCase();
    }

    function applyBlogTitle(settings) {
        var displayTitle = getDisplayBlogTitle(settings);
        var defaultTitle = getDefaultBlogTitle();
        var headerLink = document.querySelector(".blog-title");
        var root = document.documentElement;
        var baseTitle = root.dataset.baseDocumentTitle;

        if (headerLink) {
            headerLink.textContent = displayTitle;
        }

        if (!baseTitle) {
            baseTitle = document.title;
            root.dataset.baseDocumentTitle = baseTitle;
        }

        document.title = baseTitle.split(defaultTitle).join(displayTitle);
    }

    function getSettings() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return Object.assign({}, DEFAULTS);
            }
            return Object.assign({}, DEFAULTS, JSON.parse(raw));
        } catch (e) {
            return Object.assign({}, DEFAULTS);
        }
    }

    function saveSettings(settings) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }

    function defaultBackgroundColor(darkMode) {
        return darkMode ? DEFAULT_BG_DARK : DEFAULT_BG_LIGHT;
    }

    function resolveBackgroundImage(settings) {
        var custom = (settings.backgroundImage || "").trim();
        if (custom) {
            return custom;
        }
        return getDefaultBackgroundImage();
    }

    function hexToRgb(hex) {
        var value = hex.replace("#", "");
        return {
            r: parseInt(value.substring(0, 2), 16),
            g: parseInt(value.substring(2, 4), 16),
            b: parseInt(value.substring(4, 6), 16),
        };
    }

    function channelLuminance(channel) {
        var normalized = channel / 255;
        return normalized <= 0.03928
            ? normalized / 12.92
            : Math.pow((normalized + 0.055) / 1.055, 2.4);
    }

    function getLuminance(hex) {
        var rgb = hexToRgb(hex);
        return (
            0.2126 * channelLuminance(rgb.r) +
            0.7152 * channelLuminance(rgb.g) +
            0.0722 * channelLuminance(rgb.b)
        );
    }

    function isDarkBackground(hex) {
        return getLuminance(hex) < 0.45;
    }

    function applyPageContrast(root, hex) {
        root.classList.remove("custom-bg-light", "custom-bg-dark");
        root.style.removeProperty("--page-text");
        root.style.removeProperty("--page-text-muted");
        root.style.removeProperty("--page-link");

        if (!hex) {
            return;
        }

        if (isDarkBackground(hex)) {
            root.classList.add("custom-bg-dark");
            root.style.setProperty("--page-text", "#ffffff");
            root.style.setProperty("--page-text-muted", "#d8d8d8");
            root.style.setProperty("--page-link", "#9ec5e8");
        } else {
            root.classList.add("custom-bg-light");
            root.style.setProperty("--page-text", "#444444");
            root.style.setProperty("--page-text-muted", "#666666");
            root.style.setProperty("--page-link", "#529ecc");
        }
    }

    function applyAppearance(settings) {
        var root = document.documentElement;
        var darkMode = !!settings.darkMode;

        root.classList.toggle("dark-mode", darkMode);

        if (settings.backgroundColor) {
            root.style.setProperty("--bg-page", settings.backgroundColor);
            applyPageContrast(root, settings.backgroundColor);
        } else {
            root.style.removeProperty("--bg-page");
            applyPageContrast(root, "");
        }

        var bgImage = resolveBackgroundImage(settings);
        if (bgImage) {
            root.style.setProperty("--bg-image", 'url("' + bgImage.replace(/"/g, "") + '")');
        } else {
            root.style.removeProperty("--bg-image");
        }
    }

    function showSavedNotice() {
        var savedNotice = document.getElementById("settings-saved");
        if (!savedNotice) {
            return;
        }
        savedNotice.hidden = false;
        window.setTimeout(function () {
            savedNotice.hidden = true;
        }, 2000);
    }

    function persistAppearance(settings) {
        saveSettings(settings);
        applyAppearance(settings);
        showSavedNotice();
    }

    function syncColorInputs(settings, colorInput, hexInput) {
        var color = settings.backgroundColor || defaultBackgroundColor(settings.darkMode);
        if (colorInput) {
            colorInput.value = color;
        }
        if (hexInput) {
            hexInput.value = color;
        }
    }

    function setBackgroundColor(settings, value, colorInput, hexInput) {
        var normalized = normalizeHexColor(value);
        if (!normalized) {
            return false;
        }
        settings.backgroundColor = normalized;
        if (colorInput) {
            colorInput.value = normalized;
        }
        if (hexInput) {
            hexInput.value = normalized;
        }
        persistAppearance(settings);
        return true;
    }

    function initGlobalAppearance() {
        var settings = getSettings();
        var root = document.documentElement;
        if (!root.dataset.baseDocumentTitle) {
            root.dataset.baseDocumentTitle = document.title;
        }
        applyAppearance(settings);
        applyBlogTitle(settings);
    }

    function persistBlogTitle(settings) {
        saveSettings(settings);
        applyBlogTitle(settings);
        showSavedNotice();
    }

    function initCopyLinkButtons() {
        document.addEventListener("click", function (event) {
            var button = event.target.closest(".post-copy-link");
            if (!button) {
                return;
            }
            var shareUrl = button.dataset.shareUrl;
            if (!shareUrl) {
                return;
            }

            function markCopied() {
                var original = button.textContent;
                button.textContent = "Copied!";
                window.setTimeout(function () {
                    button.textContent = original;
                }, 2000);
            }

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(shareUrl).then(markCopied).catch(function () {
                    window.prompt("Copy this link:", shareUrl);
                });
            } else {
                window.prompt("Copy this link:", shareUrl);
            }
        });
    }

    function initSettingsPage() {
        var infiniteScroll = document.getElementById("infinite-scroll");
        var darkMode = document.getElementById("dark-mode");
        var backgroundColor = document.getElementById("background-color");
        var backgroundHex = document.getElementById("background-color-hex");
        var backgroundReset = document.getElementById("background-color-reset");
        var backgroundImageUrl = document.getElementById("background-image-url");
        var backgroundImageReset = document.getElementById("background-image-reset");
        var blogTitleInput = document.getElementById("blog-title");
        var blogTitleReset = document.getElementById("blog-title-reset");
        var defaultTitle = getDefaultBlogTitle();

        if (!infiniteScroll) {
            return;
        }

        var settings = getSettings();
        infiniteScroll.checked = settings.infiniteScroll;

        if (darkMode) {
            darkMode.checked = settings.darkMode;
        }

        syncColorInputs(settings, backgroundColor, backgroundHex);

        if (backgroundImageUrl) {
            backgroundImageUrl.value = settings.backgroundImage || "";
            if (!settings.backgroundImage && getDefaultBackgroundImage()) {
                backgroundImageUrl.placeholder = getDefaultBackgroundImage();
            }
        }

        if (blogTitleInput) {
            blogTitleInput.value = settings.blogTitle || "";
            blogTitleInput.placeholder = defaultTitle;
        }

        infiniteScroll.addEventListener("change", function () {
            settings.infiniteScroll = infiniteScroll.checked;
            saveSettings(settings);
            showSavedNotice();
        });

        if (blogTitleInput) {
            blogTitleInput.addEventListener("input", function () {
                settings.blogTitle = blogTitleInput.value;
                persistBlogTitle(settings);
            });
        }

        if (blogTitleReset) {
            blogTitleReset.addEventListener("click", function () {
                settings.blogTitle = "";
                if (blogTitleInput) {
                    blogTitleInput.value = "";
                }
                persistBlogTitle(settings);
            });
        }

        if (darkMode) {
            darkMode.addEventListener("change", function () {
                settings.darkMode = darkMode.checked;
                if (!settings.backgroundColor) {
                    syncColorInputs(settings, backgroundColor, backgroundHex);
                }
                persistAppearance(settings);
            });
        }

        if (backgroundColor) {
            backgroundColor.addEventListener("input", function () {
                setBackgroundColor(settings, backgroundColor.value, backgroundColor, backgroundHex);
            });
        }

        if (backgroundHex) {
            backgroundHex.addEventListener("change", function () {
                setBackgroundColor(settings, backgroundHex.value, backgroundColor, backgroundHex);
            });
            backgroundHex.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    setBackgroundColor(settings, backgroundHex.value, backgroundColor, backgroundHex);
                }
            });
        }

        if (backgroundReset) {
            backgroundReset.addEventListener("click", function () {
                settings.backgroundColor = "";
                syncColorInputs(settings, backgroundColor, backgroundHex);
                persistAppearance(settings);
            });
        }

        if (backgroundImageUrl) {
            backgroundImageUrl.addEventListener("change", function () {
                settings.backgroundImage = backgroundImageUrl.value.trim();
                persistAppearance(settings);
            });
        }

        if (backgroundImageReset) {
            backgroundImageReset.addEventListener("click", function () {
                settings.backgroundImage = "";
                if (backgroundImageUrl) {
                    backgroundImageUrl.value = "";
                }
                persistAppearance(settings);
            });
        }
    }

    function initFeedPage() {
        var feed = document.getElementById("post-feed");
        var pagination = document.getElementById("pagination");
        var sentinel = document.getElementById("infinite-scroll-sentinel");
        var loadingEl = document.getElementById("infinite-scroll-loading");
        var endEl = document.getElementById("infinite-scroll-end");

        if (!feed || !getSettings().infiniteScroll) {
            return;
        }

        var currentPage = parseInt(feed.dataset.page, 10) || 1;
        var totalPages = parseInt(feed.dataset.totalPages, 10) || 1;
        var tag = feed.dataset.tag || "";
        var loading = false;

        if (pagination) {
            pagination.hidden = true;
        }
        if (sentinel) {
            sentinel.hidden = false;
        }

        if (currentPage >= totalPages && endEl) {
            endEl.hidden = false;
            return;
        }

        function buildApiUrl(page) {
            var url = "/api/posts?page=" + page;
            if (tag) {
                url += "&tag=" + encodeURIComponent(tag);
            }
            if (feed.dataset.type) {
                url += "&type=" + encodeURIComponent(feed.dataset.type);
            }
            if (feed.dataset.search) {
                url += "&q=" + encodeURIComponent(feed.dataset.search);
            }
            if (feed.dataset.year) {
                url += "&year=" + encodeURIComponent(feed.dataset.year);
            }
            if (feed.dataset.month) {
                url += "&month=" + encodeURIComponent(feed.dataset.month);
            }
            return url;
        }

        function loadMore() {
            if (loading || currentPage >= totalPages) {
                return;
            }

            loading = true;
            if (loadingEl) {
                loadingEl.hidden = false;
            }

            fetch(buildApiUrl(currentPage + 1))
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("Failed to load posts");
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (data.html) {
                        feed.insertAdjacentHTML("beforeend", data.html);
                    }
                    currentPage = data.page;
                    totalPages = data.total_pages;

                    if (loadingEl) {
                        loadingEl.hidden = true;
                        loadingEl.textContent = "Loading more posts…";
                    }

                    if (!data.has_more && endEl) {
                        endEl.hidden = false;
                        if (observer && sentinel) {
                            observer.unobserve(sentinel);
                        }
                    }
                })
                .catch(function () {
                    if (loadingEl) {
                        loadingEl.textContent = "Couldn't load more posts. Scroll to try again.";
                        loadingEl.hidden = false;
                    }
                })
                .finally(function () {
                    loading = false;
                });
        }

        var observer = null;
        if (sentinel && "IntersectionObserver" in window) {
            observer = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            loadMore();
                        }
                    });
                },
                { rootMargin: "200px" }
            );
            observer.observe(sentinel);
        } else {
            window.addEventListener("scroll", function () {
                if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
                    loadMore();
                }
            });
        }
    }

    function initPhotoLightbox() {
        var lightbox = document.createElement("div");
        lightbox.id = "photo-lightbox";
        lightbox.className = "photo-lightbox";
        lightbox.hidden = true;
        lightbox.innerHTML =
            '<button type="button" class="lightbox-close" aria-label="Close">&times;</button>' +
            '<button type="button" class="lightbox-prev" aria-label="Previous image">&lsaquo;</button>' +
            '<img class="lightbox-image" alt="">' +
            '<button type="button" class="lightbox-next" aria-label="Next image">&rsaquo;</button>';
        document.body.appendChild(lightbox);

        var imageEl = lightbox.querySelector(".lightbox-image");
        var images = [];
        var currentIndex = 0;

        function collectImages() {
            images = Array.prototype.slice.call(
                document.querySelectorAll(".post-content img[src]")
            );
        }

        function show(index) {
            if (!images.length) {
                return;
            }
            currentIndex = (index + images.length) % images.length;
            imageEl.src = images[currentIndex].src;
            imageEl.alt = images[currentIndex].alt || "Photo";
            lightbox.hidden = false;
            document.body.style.overflow = "hidden";
        }

        function hide() {
            lightbox.hidden = true;
            document.body.style.overflow = "";
            imageEl.removeAttribute("src");
        }

        document.addEventListener("click", function (event) {
            var img = event.target.closest(".post-content img");
            if (!img || !img.src) {
                return;
            }
            collectImages();
            var index = images.indexOf(img);
            if (index === -1) {
                return;
            }
            event.preventDefault();
            show(index);
        });

        lightbox.querySelector(".lightbox-close").addEventListener("click", hide);
        lightbox.querySelector(".lightbox-prev").addEventListener("click", function () {
            show(currentIndex - 1);
        });
        lightbox.querySelector(".lightbox-next").addEventListener("click", function () {
            show(currentIndex + 1);
        });
        lightbox.addEventListener("click", function (event) {
            if (event.target === lightbox) {
                hide();
            }
        });
        document.addEventListener("keydown", function (event) {
            if (lightbox.hidden) {
                return;
            }
            if (event.key === "Escape") {
                hide();
            } else if (event.key === "ArrowLeft") {
                show(currentIndex - 1);
            } else if (event.key === "ArrowRight") {
                show(currentIndex + 1);
            }
        });
    }

    window.tumbl = {
        getSettings: getSettings,
        saveSettings: saveSettings,
        applyAppearance: applyAppearance,
        applyBlogTitle: applyBlogTitle,
        initGlobalAppearance: initGlobalAppearance,
        initSettingsPage: initSettingsPage,
        initFeedPage: initFeedPage,
        initPhotoLightbox: initPhotoLightbox,
    };

    initGlobalAppearance();
    initCopyLinkButtons();
    initPhotoLightbox();
})();
