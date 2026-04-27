* {
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Reduce motion for users who prefer it */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.8);
}

.App {
  min-height: 100vh;
  background: #f8fafc;
}

.dark-section {
  background: #0f172a;
  color: #f8fafc;
}

.glass-card {
  backdrop-filter: blur(16px);
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dark .glass-card {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.hero-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.15), transparent 50%);
  pointer-events: none;
}

.btn-primary {
  background: #0f172a;
  color: #f8fafc;
  padding: 0.75rem 2rem;
  border-radius: 0.5rem;
  font-weight: 500;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.btn-primary:hover {
  background: #1e293b;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-1px);
}

.btn-secondary {
  background: #f1f5f9;
  color: #0f172a;
  padding: 0.75rem 2rem;
  border-radius: 0.5rem;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;


/* Loading animations */
@keyframes pulse-fast {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.animate-pulse-fast {
  animation: pulse-fast 1s ease-in-out infinite;
}

/* Fade in animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out;
}

/* Image lazy loading placeholder */
img[loading="lazy"] {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Button transitions */
button {
  transition: all 0.2s ease;
}

/* Card hover effects */
.card-hover {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

/* Typing animation */
@keyframes typing-dot {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-pending {
  background: #fef3c7;
  color: #92400e;
}

.status-in_progress {
  background: #dbeafe;
  color: #1e40af;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-approved {
  background: #d1fae5;
  color: #065f46;
}

.status-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.rtl-layout {
  direction: rtl;
  text-align: right;
}
