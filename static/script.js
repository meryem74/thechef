document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("restaurantSearch");
    const restaurantCards = document.querySelectorAll(".restaurant-card");

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase();
        restaurantCards.forEach(card => {
            const name = card.querySelector(".restaurant-name").textContent.toLowerCase();
            card.style.display = name.includes(query) ? "block" : "none";
        });
    });
});
