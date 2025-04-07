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
    submitButton = document.getElementById('submitButton');

    // Hide the result banners
    successBanner.style.display = 'none';
    errorBanner.style.display = 'none';
    submitButton.disabled = true;

    // Show loading banner
    loadingBanner.style.display = 'flex';
    const number = document.getElementById('numberInput').value;
        fetch(`/api/v1/uisp-import/nn/${number}/`, {
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
            submitButton.disabled = false;
        })
        .catch(error => {
            document.getElementById('errorDetail').innerHTML = `${error}`;
            loadingBanner.style.display = 'none';
            errorBanner.style.display = 'flex';
            submitButton.disabled = false;
        });
}
