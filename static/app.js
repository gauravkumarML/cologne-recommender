document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('preferenceInput');
    const genderFilter = document.getElementById('genderFilter');
    const searchBtn = document.getElementById('searchBtn');
    const suggestions = document.querySelectorAll('.suggestion-chip');
    const loader = document.getElementById('loader');
    const resultsSection = document.getElementById('resultsSection');
    const template = document.getElementById('fragranceCardTemplate');

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
                    gender: genderFilter ? genderFilter.value : "All"
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
        clone.querySelector('.match-percentage').textContent = `${matchPercent}% Match`;

        const notesContainer = clone.querySelector('.notes-container');

        if (item.notes && item.notes.length > 0) {
            // Show up to 8 notes
            const displayNotes = item.notes.slice(0, 8);
            displayNotes.forEach(note => {
                const span = document.createElement('span');
                span.className = 'note-tag';
                span.textContent = note;
                notesContainer.appendChild(span);
            });

            if (item.notes.length > 8) {
                const moreSpan = document.createElement('span');
                moreSpan.className = 'note-tag';
                moreSpan.style.background = 'transparent';
                moreSpan.style.border = 'none';
                moreSpan.textContent = `+${item.notes.length - 8} more`;
                notesContainer.appendChild(moreSpan);
            }
        } else {
            notesContainer.innerHTML = '<span class="note-tag" style="opacity: 0.5;">Notes unavailable</span>';
        }

        resultsSection.appendChild(clone);
    }
});
