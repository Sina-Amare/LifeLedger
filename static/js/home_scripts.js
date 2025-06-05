document.addEventListener("DOMContentLoaded", function () {
  // Initialize Intersection Observer for scroll animations
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.15, // Trigger when 15% of the element is visible
  };

  const intersectionObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        // console.log("Element visible:", entry.target); // Debug log

        // If the element is a stat number, attempt to start its animation
        if (entry.target.classList.contains("stat-number")) {
          startAnimation(entry.target);
          // No need to unobserve here if startAnimation handles the "once" logic
        }
        // For other general scroll animations, unobserve after first intersection
        // to prevent re-triggering if the element is not a stat number.
        // However, if you want other .animate-on-scroll elements to re-animate
        // if they scroll out and back in, you'd remove this unobserve.
        // For now, keeping it for general elements but stat numbers handle it internally.
        // else {
        //    observer.unobserve(entry.target);
        // }
      }
    });
  }, observerOptions);

  const elementsToAnimate = document.querySelectorAll(".animate-on-scroll");
  elementsToAnimate.forEach((el) => {
    intersectionObserver.observe(el);
  });

  // Animate Hero Title letter by letter
  const heroTitle = document.querySelector(".hero-title-creative");
  if (heroTitle) {
    const text = heroTitle.textContent.trim();
    heroTitle.innerHTML = ""; // Clear original text

    text.split("").forEach((char, index) => {
      const span = document.createElement("span");
      span.textContent = char === " " ? "\u00A0" : char; // Handle spaces
      // Apply animation delay for staggered effect
      span.style.animationDelay = `${0.5 + index * 0.05}s`;
      heroTitle.appendChild(span);
    });
  }

  // Parallax Effect for Feature Images
  const featureImages = document.querySelectorAll(
    ".feature-image-wrapper-creative img"
  );
  featureImages.forEach((img) => {
    const parentWrapper = img.parentElement;
    if (parentWrapper) {
      parentWrapper.addEventListener("mousemove", (e) => {
        const rect = parentWrapper.getBoundingClientRect();
        // Calculate mouse position relative to the center of the wrapper
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        // Determine movement strength (adjust multiplier for more/less effect)
        const moveX = (x / rect.width) * 15; // Reduced multiplier for less extreme movement
        const moveY = (y / rect.height) * 15;
        // Apply transform to the image
        img.style.transform = `translate(${moveX}px, ${moveY}px) scale(1.03)`; // Slightly reduced scale
        img.style.transition = "transform 0.1s linear"; // Smooth transition for mouse move
      });
      parentWrapper.addEventListener("mouseleave", () => {
        // Reset image transform on mouse leave
        img.style.transform = "translate(0, 0) scale(1)";
        img.style.transition = "transform 0.3s ease-out"; // Smooth transition back to original state
      });
    }
  });

  // Hero Section Particles (kept as is from your code)
  const heroSection = document.querySelector(".hero-section-bg-overlay");
  if (heroSection) {
    const canvas = document.createElement("canvas");
    canvas.id = "hero-particles";
    // Ensure canvas is behind the z-[2] content but above the background image
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.zIndex = "1"; // Behind .relative.z-[2] but above .hero-bg-image-creative (which is also absolute)
    heroSection.insertBefore(canvas, heroSection.firstChild); // Insert before other children

    const ctx = canvas.getContext("2d");

    // Debounce resize function
    let resizeTimeout;
    const debouncedResize = () => {
      canvas.width = heroSection.offsetWidth;
      canvas.height = heroSection.offsetHeight;
    };

    window.addEventListener("resize", () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(debouncedResize, 100);
    });
    debouncedResize(); // Initial size set

    const particles = [];
    const particleCount = Math.min(50, Math.floor(canvas.width / 30)); // Adjust particle count based on width
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 2.5 + 0.5, // Slightly smaller particles
        speed: Math.random() * 0.8 + 0.2, // Slightly slower speed
        delay: Math.random() * 10,
        opacity: Math.random() * 0.5 + 0.3, // Add opacity
      });
    }

    function animateParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((particle) => {
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        const isDark = document.documentElement.classList.contains("dark");
        ctx.fillStyle = isDark
          ? `rgba(200, 210, 255, ${particle.opacity * 0.7})` // More subtle in dark mode
          : `rgba(255, 255, 255, ${particle.opacity})`;
        ctx.fill();

        particle.y -= particle.speed;
        if (particle.y + particle.radius < 0)
          particle.y = canvas.height + particle.radius;

        // Smoother horizontal movement
        particle.x += Math.sin(particle.delay + particle.y * 0.015) * 1.5;
        if (particle.x + particle.radius < 0)
          particle.x = canvas.width + particle.radius;
        if (particle.x - particle.radius > canvas.width)
          particle.x = -particle.radius;
      });
      requestAnimationFrame(animateParticles);
    }
    if (particles.length > 0) {
      // Only start animation if particles exist
      animateParticles();
    }
  }

  // Quick Stats Number Animation with Easing - Animate Only Once
  function startAnimation(statElement) {
    // Check if this element has already been animated
    if (statElement.dataset.animated === "true") {
      // console.log("Animation already done for:", statElement); // Debug log
      return; // Don't animate again
    }

    const target = parseInt(statElement.getAttribute("data-target"));
    if (isNaN(target)) {
      console.error("Invalid data-target for stat animation:", statElement);
      statElement.textContent =
        statElement.getAttribute("data-target") || "N/A"; // Display original target or N/A
      statElement.dataset.animated = "true"; // Mark as "processed" to avoid re-trying
      return;
    }

    let count = 0;
    const duration = 2000; // 2 seconds for the animation
    const startTime = performance.now();

    // console.log("Starting animation for:", statElement, "Target:", target); // Debug log
    statElement.dataset.animated = "true"; // Mark as animated right at the start

    const easeOutQuad = (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t); // Easing function

    function updateCount(currentTime) {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1); // Progress from 0 to 1
      const easedProgress = easeOutQuad(progress); // Apply easing
      count = Math.floor(easedProgress * target);

      if (progress < 1) {
        statElement.textContent = count.toLocaleString(); // Format with commas
        requestAnimationFrame(updateCount); // Continue animation
      } else {
        statElement.textContent = target.toLocaleString(); // Ensure final target is set
        // console.log("Animation finished for:", statElement); // Debug log
      }
    }
    requestAnimationFrame(updateCount); // Start the animation loop
  }

  const statNumbers = document.querySelectorAll(".stat-number");
  statNumbers.forEach((stat) => {
    // The IntersectionObserver will call startAnimation when the element is visible.
    // startAnimation itself now handles the "once" logic.
    intersectionObserver.observe(stat);
  });

  // Testimonial Slider
  const testimonialSlider = document.querySelector(".testimonial-slider");
  const slides = document.querySelectorAll(".testimonial-card-artistic");
  const slideContainer = document.querySelector(".testimonial-slides");
  const prevButton = document.getElementById("prev-slide");
  const nextButton = document.getElementById("next-slide");
  let currentIndex = 0;
  let autoSlideInterval;

  function showSlide(index) {
    if (!slideContainer || slides.length === 0) return;

    if (index >= slides.length) {
      index = 0;
    } else if (index < 0) {
      index = slides.length - 1;
    }

    slideContainer.style.transform = `translateX(-${index * 100}%)`;
    currentIndex = index;

    // Update active state for pagination dots (if you add them)
  }

  function startAutoSlide() {
    stopAutoSlide(); // Clear existing interval before starting a new one
    autoSlideInterval = setInterval(() => {
      showSlide(currentIndex + 1);
    }, 5000); // Change slide every 5 seconds
  }

  function stopAutoSlide() {
    clearInterval(autoSlideInterval);
  }

  if (
    testimonialSlider &&
    slides.length > 0 &&
    slideContainer &&
    prevButton &&
    nextButton
  ) {
    prevButton.addEventListener("click", () => {
      showSlide(currentIndex - 1);
      stopAutoSlide(); // Stop auto-slide on manual navigation
      // Optionally restart auto-slide after a delay:
      // setTimeout(startAutoSlide, 10000); // Restart after 10 seconds of inactivity
    });

    nextButton.addEventListener("click", () => {
      showSlide(currentIndex + 1);
      stopAutoSlide();
      // setTimeout(startAutoSlide, 10000);
    });

    // Pause auto-slide on hover
    testimonialSlider.addEventListener("mouseenter", stopAutoSlide);
    testimonialSlider.addEventListener("mouseleave", startAutoSlide);

    // Show the first slide initially and start auto-slide
    showSlide(currentIndex);
    startAutoSlide();
  } else {
    console.warn(
      "Testimonial slider elements not found, slider functionality disabled."
    );
  }
});
