function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

async function updateTaskStatusTable() {
    const taskStatusTable = document.getElementById('taskStatusTable').getElementsByTagName('tbody')[0];
    const loadingTaskStatusTable = document.getElementById('loadingTaskStatusTable');

    const status = await fetch(`/api/v1/uisp-import/status/`, {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
    });
    const j = await status.json();

    taskStatusTable.innerHTML = `
        <tr>
            <th>ID</th><th>NN</th><th>Status</th>
        </tr>
    `;

    j.tasks.forEach(task => {

        const row = taskStatusTable.insertRow();
        const cellId = row.insertCell(0);
        const cellName = row.insertCell(1);
        const cellValue = row.insertCell(2);

        cellId.textContent = task.id;
        cellName.textContent = task.nn;
        cellValue.textContent = task.status;
    });

    loadingTaskStatusTable.style.display = 'none';
}

async function submitForm(event) {
    loadingBanner = document.getElementById('loadingBanner');
    successBanner = document.getElementById('successBanner');
    errorBanner = document.getElementById('errorBanner');
    errorDetail = document.getElementById('errorDetail');
    successBanner = document.getElementById('successBanner');
    successDetail = document.getElementById('successDetail');
    submitButton = document.getElementById('submitButton');

    taskStatusTable = document.getElementById('taskStatusTable');

    event.preventDefault();
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
            successDetail.innerHTML = `UISP Import ${data.task_id} is now running for NN${number}.`;
            loadingBanner.style.display = 'none';
            successBanner.style.display = 'flex';
            submitButton.disabled = false;
            loadingTaskStatusTable.style.display = 'flex';
        })
        .catch(error => {
            errorDetail.innerHTML = `${error}`;
            loadingBanner.style.display = 'none';
            errorBanner.style.display = 'flex';
            submitButton.disabled = false;
        });

    await updateTaskStatusTable();
}
