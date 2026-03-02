document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('preferenceInput');
    const genderTabs = document.querySelectorAll('#genderTabs .segment');
    const searchBtn = document.getElementById('searchBtn');
    const suggestions = document.querySelectorAll('.suggestion-chip');
    const loader = document.getElementById('loader');
    const resultsSection = document.getElementById('resultsSection');
    const template = document.getElementById('fragranceCardTemplate');

    let currentGender = "All";

    // Handle segmented control clicks
    genderTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            genderTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentGender = tab.getAttribute('data-value');
        });
    });

    // Handle suggestion clicks
    suggestions.forEach(chip => {
        chip.addEventListener('click', () => {
            // Extract text without quotes
            const text = chip.textContent.replace(/"/g, '');
            searchInput.value = text;
            performSearch(text);
        });
    });

    // Handle button click
    searchBtn.addEventListener('click', () => {
        const query = searchInput.value.trim();
        if (query) {
            performSearch(query);
        }
    });

    // Handle enter key
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const query = searchInput.value.trim();
            if (query) {
                performSearch(query);
            }
        }
    });

    async function performSearch(query) {
        // Show loader, hide results
        resultsSection.innerHTML = '';
        resultsSection.classList.add('hidden');
        loader.classList.remove('hidden');

        try {
            const response = await fetch('/recommend/quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    preferences: query,
                    top_k: 6, // Show top 6 matches
                    gender: currentGender
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            // Hide loader
            loader.classList.add('hidden');

            // Render results
            if (data.length === 0) {
                resultsSection.innerHTML = '<p class="error-msg">No matches found. Try modifying your search.</p>';
            } else {
                data.forEach((item, index) => {
                    renderCard(item, index);
                });
            }
            resultsSection.classList.remove('hidden');

        } catch (error) {
            console.error('Error fetching recommendations:', error);
            loader.classList.add('hidden');
            resultsSection.innerHTML = '<p class="error-msg" style="color: #ef4444; font-weight: 500; text-align: center; grid-column: 1/-1;">Could not reach the recommendation engine. Please try again later.</p>';
            resultsSection.classList.remove('hidden');
        }
    }

    function renderCard(data, index) {
        const item = data.cologne;
        const matchPercent = data.match;

        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.fragrance-card');

        // Stagger animation
        card.style.animationDelay = `${index * 0.1}s`;

        clone.querySelector('.brand-name').textContent = item.brand;
        clone.querySelector('.fragrance-name').textContent = item.name;

        clone.querySelector('.match-percentage-text').textContent = `MATCH: ${matchPercent}%`;

        const notesContainer = clone.querySelector('.notes-container');

        if (item.notes && item.notes.length > 0) {
            // Show up to 8 notes
            const displayNotes = item.notes.slice(0, 8);
            const notesString = displayNotes.join(' / ').toUpperCase();

            const span = document.createElement('span');
            span.className = 'note-tag';
            span.textContent = notesString;

            if (item.notes.length > 8) {
                span.textContent += ` / +${item.notes.length - 8} MORE`;
            }
            notesContainer.appendChild(span);
        } else {
            notesContainer.innerHTML = '<span class="note-tag" style="opacity: 0.5;">NOTES UNAVAILABLE</span>';
        }

        resultsSection.appendChild(clone);
    }
});
