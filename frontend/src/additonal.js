document.addEventListener("click", function(e) {
  const bubble = document.createElement("div");
  bubble.classList.add("bubble");

  // FIX: use pageX & pageY
  bubble.style.left = e.pageX + "px";
  bubble.style.top = e.pageY + "px";

  document.body.appendChild(bubble);

  setTimeout(() => {
    bubble.remove();
  }, 600);
});