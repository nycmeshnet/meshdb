function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
      }

async function submitForm(event) {
    event.preventDefault();

    loadingBanner = document.getElementById('loadingBanner');
    successBanner = document.getElementById('successBanner');
    errorBanner = document.getElementById('errorBanner');

    // Hide the result banners
    successBanner.style.display = 'none';
    errorBanner.style.display = 'none';

    // Show loading banner
    loadingBanner.style.display = 'flex';
    const number = document.getElementById('numberInput').value;
        fetch(`/api/v1/crawl-uisp/nn/${number}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(async response => {
            if (!response.ok) {
                const j = await response.json()
                throw new Error(`${response.status} ${j.detail}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data.status);
            loadingBanner.style.display = 'none';
            successBanner.style.display = 'flex';
        })
        .catch(error => {
            document.getElementById('errorDetail').innerHTML = `${error}`;
            loadingBanner.style.display = 'none';
            errorBanner.style.display = 'flex';
        });
}
