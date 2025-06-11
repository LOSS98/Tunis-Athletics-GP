function toggleStartlistPdf() {
    const viewer = document.getElementById('startlistPdfViewer');
    const toggleText = document.getElementById('startlistToggleText');

    if (viewer.classList.contains('hidden')) {
        viewer.classList.remove('hidden');
        toggleText.textContent = 'Hide Start List PDF';
        viewer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        viewer.classList.add('hidden');
        toggleText.textContent = 'View Start List PDF';
    }
}

function toggleResultsPdf() {
    const viewer = document.getElementById('resultsPdfViewer');
    const toggleText = document.getElementById('resultsToggleText');

    if (viewer.classList.contains('hidden')) {
        viewer.classList.remove('hidden');
        toggleText.textContent = 'Hide Results PDF';
        viewer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        viewer.classList.add('hidden');
        toggleText.textContent = 'View Results PDF';
    }
}

function togglePdfViewer() {
    const viewer = document.getElementById('pdfViewer');
    const toggleText = document.getElementById('pdfToggleText');

    if (viewer.classList.contains('hidden')) {
        viewer.classList.remove('hidden');
        toggleText.textContent = 'Hide PDF';
        viewer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        viewer.classList.add('hidden');
        toggleText.textContent = 'View PDF';
    }
}