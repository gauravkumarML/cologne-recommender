document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('preferenceInput');
    const genderTabs = document.querySelectorAll('#genderTabs .segment');
    const searchBtn = document.getElementById('searchBtn');
    const suggestions = document.querySelectorAll('.suggestion-chip');
    const loader = document.getElementById('loader');
    const resultsSection = document.getElementById('resultsSection');
    const template = document.getElementById('fragranceCardTemplate');

    let currentGender = "All";

    // 1. Ambient Background Interaction
    document.addEventListener('mousemove', (e) => {
        const x = (window.innerWidth / 2 - e.pageX) / 30;
        const y = (window.innerHeight / 2 - e.pageY) / 30;
        gsap.to('.mesh-1', { x: x, y: y, duration: 1, ease: 'power2.out' });
        gsap.to('.mesh-2', { x: x * -1.5, y: y * -1.5, duration: 1.5, ease: 'power2.out' });
        gsap.to('.mesh-3', { x: x * 0.5, y: y * 0.5, duration: 1.2, ease: 'power2.out' });
    });

    // 2. Magnetic Micro-interactions
    const magneticElements = document.querySelectorAll('.primary-btn, .segment');
    magneticElements.forEach(elem => {
        elem.addEventListener('mousemove', (e) => {
            const rect = elem.getBoundingClientRect();
            const x = (e.clientX - rect.left - rect.width / 2) * 0.4;
            const y = (e.clientY - rect.top - rect.height / 2) * 0.4;
            gsap.to(elem, { x: x, y: y, duration: 0.3, ease: 'power2.out' });
        });
        elem.addEventListener('mouseleave', () => {
            gsap.to(elem, { x: 0, y: 0, duration: 1, ease: "elastic.out(1, 0.3)" });
        });
    });

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

                // 3. Staggered Spring Reveal
                gsap.fromTo('.fragrance-card',
                    { y: 50, opacity: 0 },
                    { y: 0, opacity: 1, duration: 1, stagger: 0.15, ease: "back.out(1.7)" }
                );
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

        // 4. 3D Tilt Hover & Lighting
        const shimmer = document.createElement('div');
        shimmer.className = 'shimmer';
        card.appendChild(shimmer);

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            gsap.to(card, {
                rotateY: (x / rect.width) * 15,
                rotateX: -(y / rect.height) * 15,
                duration: 0.5,
                ease: 'power2.out',
                transformPerspective: 1000,
                transformOrigin: "center"
            });

            gsap.to(shimmer, {
                backgroundPosition: `${((x / rect.width) + 0.5) * 100}% ${((y / rect.height) + 0.5) * 100}%`,
                duration: 0.5,
                ease: "power2.out",
                opacity: 1
            });
        });

        card.addEventListener('mouseleave', () => {
            gsap.to(card, { rotateY: 0, rotateX: 0, duration: 1, ease: "elastic.out(1, 0.3)" });
            gsap.to(shimmer, { opacity: 0, duration: 0.5, ease: "power2.out" });
        });

        resultsSection.appendChild(clone);
    }
});
