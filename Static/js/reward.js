// REFRESH INTERVAL (every 10 seconds)
setInterval(() => {
    fetch('/rewards/data')
        .then(response => response.json())
        .then(data => {
            // Update top referrers
            ['day', 'week', 'month', 'year'].forEach(period => {
                const table = document.getElementById(`top-${period}-table`);
                if (table && data[`top_${period}`]) {
                    table.innerHTML = '';
                    data[`top_${period}`].forEach((user, index) => {
                        table.innerHTML += `
                            <tr>
                                <td>${index + 1}</td>
                                <td>${user.username}</td>
                                <td>${user.invite_count}</td>
                            </tr>
                        `;
                    });
                }
            });

            // Update user's personal counters
            ['today', 'week', 'month', 'year'].forEach(period => {
                const span = document.getElementById(`my-invites-${period}`);
                if (span && data[`my_${period}`]) {
                    span.textContent = data[`my_${period}`];
                }
            });
        });
}, 10000); // 10 seconds

// COUNTDOWN TO RESET
function getNextResetTime(type) {
    const now = new Date();
    if (type === 'day') {
        return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    } else if (type === 'week') {
        const day = now.getDay();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate() + (7 - day));
    } else if (type === 'month') {
        return new Date(now.getFullYear(), now.getMonth() + 1, 1);
    } else if (type === 'year') {
        return new Date(now.getFullYear() + 1, 0, 1);
    }
}

function updateCountdowns() {
    ['day', 'week', 'month', 'year'].forEach(type => {
        const resetTime = getNextResetTime(type);
        const now = new Date();
        const diff = resetTime - now;

        if (diff > 0) {
            const hours = Math.floor(diff / 1000 / 60 / 60);
            const minutes = Math.floor((diff / 1000 / 60) % 60);
            const seconds = Math.floor((diff / 1000) % 60);
            const display = document.getElementById(`${type}-countdown`);
            if (display) {
                display.textContent = `${hours}h ${minutes}m ${seconds}s`;
            }
        }
    });
}
setInterval(updateCountdowns, 1000);
updateCountdowns();
