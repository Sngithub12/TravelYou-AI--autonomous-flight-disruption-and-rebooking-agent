document.querySelectorAll("td").forEach((cell) => {
  if (cell.textContent.trim() === "0") {
    cell.setAttribute("title", "Nonstop or no fare increase, depending on column");
  }
});
