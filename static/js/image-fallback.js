/**
 * Image Fallback Handler
 * Automatically replaces broken images with default placeholders
 */

const ImageFallback = {
  DEFAULT_AVATAR: '/static/images/default/default_avatar.png',
  DEFAULT_PRODUCT: '/static/images/default/default_product.png',
  DEFAULT_ICON: '/static/images/default/default_icon.png',

  /**
   * Initialize image fallback handlers on all images
   */
  init() {
    // Handle all images on page load
    document.addEventListener('DOMContentLoaded', () => {
      this.setupFallbacks();
    });

    // Also handle dynamically added images
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.tagName === 'IMG') {
            this.setupImageFallback(node);
          } else if (node.querySelectorAll) {
            const images = node.querySelectorAll('img');
            images.forEach((img) => this.setupImageFallback(img));
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  },

  /**
   * Setup fallback for all existing images
   */
  setupFallbacks() {
    const images = document.querySelectorAll('img');
    images.forEach((img) => {
      this.setupImageFallback(img);
    });
  },

  /**
   * Setup fallback for a single image
   */
  setupImageFallback(img) {
    // Determine which default to use based on data attribute or class
    let defaultImage = this.DEFAULT_ICON;

    if (img.dataset.type === 'avatar' || img.classList.contains('avatar-image')) {
      defaultImage = this.DEFAULT_AVATAR;
    } else if (img.dataset.type === 'product' || img.classList.contains('product-image')) {
      defaultImage = this.DEFAULT_PRODUCT;
    }

    // Handle error event
    img.addEventListener('error', () => {
      if (img.src !== defaultImage) {
        img.src = defaultImage;
        img.classList.add('image-fallback-active');
      }
    }, { once: true });

    // Also check if image failed to load immediately
    if (!img.complete || img.naturalHeight === 0) {
      if (img.src && !img.src.includes('/default/')) {
        img.src = defaultImage;
        img.classList.add('image-fallback-active');
      }
    }
  },
};

// Auto-initialize on script load
ImageFallback.init();
