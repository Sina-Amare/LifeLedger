document.addEventListener("DOMContentLoaded", function () {
  // Initialize Intersection Observer for scroll animations
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.15,
  };

  const intersectionObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        console.log("Element visible:", entry.target); // Debug log
        if (entry.target.classList.contains("stat-number")) {
          startAnimation(entry.target);
        }
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
    heroTitle.innerHTML = "";

    text.split("").forEach((char, index) => {
      const span = document.createElement("span");
      span.textContent = char === " " ? "\u00A0" : char;
      span.style.animationDelay = `${0.5 + index * 0.05}s`;
      heroTitle.appendChild(span);
    });
  }

  // Parallax Effect for Feature Images
  const featureImages = document.querySelectorAll(
    ".feature-image-wrapper-creative img"
  );
  featureImages.forEach((img) => {
    img.parentElement.addEventListener("mousemove", (e) => {
      const rect = img.parentElement.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      const moveX = (x / rect.width) * 20;
      const moveY = (y / rect.height) * 20;
      img.style.transform = `translate(${moveX}px, ${moveY}px) scale(1.05)`;
    });
    img.parentElement.addEventListener("mouseleave", () => {
      img.style.transform = "translate(0, 0) scale(1)";
    });
  });

  // Hero Section Particles
  const heroSection = document.querySelector(".hero-section-bg-overlay");
  if (heroSection) {
    const canvas = document.createElement("canvas");
    canvas.id = "hero-particles";
    heroSection.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    canvas.width = heroSection.offsetWidth;
    canvas.height = heroSection.offsetHeight;

    window.addEventListener("resize", () => {
      canvas.width = heroSection.offsetWidth;
      canvas.height = heroSection.offsetHeight;
    });

    const particles = [];
    const particleCount = 50;
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 3 + 1,
        speed: Math.random() * 1 + 0.5,
        delay: Math.random() * 10,
      });
    }

    function animateParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((particle) => {
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fillStyle = document.documentElement.classList.contains("dark")
          ? "rgba(200, 210, 255, 0.5)"
          : "rgba(255, 255, 255, 0.6)";
        ctx.fill();

        particle.y -= particle.speed;
        if (particle.y < 0) particle.y = canvas.height;
        particle.x += Math.sin(particle.delay + particle.y * 0.02) * 2;
        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
      });
      requestAnimationFrame(animateParticles);
    }
    animateParticles();
  }

  // Quick Stats Number Animation with Easing
  function startAnimation(statElement) {
    const target = parseInt(statElement.getAttribute("data-target"));
    let count = 0;
    const duration = 2000; // 2 seconds for the animation
    const startTime = performance.now();

    console.log("Starting animation for:", statElement, "Target:", target); // Debug log

    const easeOutQuad = (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t);

    function updateCount(currentTime) {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      const easedProgress = easeOutQuad(progress);
      count = Math.floor(easedProgress * target);

      if (progress < 1) {
        statElement.textContent = count.toLocaleString();
        requestAnimationFrame(updateCount);
      } else {
        statElement.textContent = target.toLocaleString();
      }
    }

    requestAnimationFrame(updateCount);
  }

  const statNumbers = document.querySelectorAll(".stat-number");
  statNumbers.forEach((stat) => {
    intersectionObserver.observe(stat);
  });

  // Testimonial Slider
  const slides = document.querySelectorAll(".testimonial-card-artistic");
  const slideContainer = document.querySelector(".testimonial-slides");
  let currentIndex = 0;

  function showSlide(index) {
    if (index >= slides.length) index = 0;
    if (index < 0) index = slides.length - 1;
    slides.forEach((slide, i) => {
      slide.classList.remove("active");
      if (i === index) {
        slide.classList.add("active");
      }
    });
    slideContainer.style.transform = `translateX(-${index * 100}%)`;
    currentIndex = index;
  }

  document.getElementById("next-slide").addEventListener("click", () => {
    showSlide(currentIndex + 1);
  });

  document.getElementById("prev-slide").addEventListener("click", () => {
    showSlide(currentIndex - 1);
  });

  // Show the first slide initially
  showSlide(currentIndex);
});
