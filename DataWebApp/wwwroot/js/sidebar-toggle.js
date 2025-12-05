/**
 * Sidebar Toggle Functionality (Right Side)
 * Handles opening/closing the filter sidebar and layout adjustments
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeSidebar();
    initializeLayoutOptions();
});

/**
 * Initialize sidebar toggle functionality
 */
function initializeSidebar() {
    const sidebar = document.getElementById('kpiSidebar');
    const mainContent = document.getElementById('kpiMainContent');
    const toggleTab = document.getElementById('sidebarToggleTab');
    const closeBtn = document.getElementById('sidebarCloseBtn');

    if (!sidebar || !mainContent || !toggleTab || !closeBtn) {
        console.warn('Sidebar elements not found');
        return;
    }

    // Open sidebar when toggle tab is clicked
    toggleTab.addEventListener('click', function (e) {
        e.stopPropagation();
        sidebar.classList.add('open');
        mainContent.classList.add('sidebar-open');
        toggleTab.style.opacity = '0';
        toggleTab.style.pointerEvents = 'none';
    });

    // Close sidebar when close button is clicked
    closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        closeSidebar();
    });

    // Close sidebar when clicking outside
    document.addEventListener('click', function (event) {
        const isClickInsideSidebar = sidebar.contains(event.target);
        const isClickOnToggleTab = toggleTab.contains(event.target);

        if (!isClickInsideSidebar && !isClickOnToggleTab && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // Handle ESC key to close sidebar
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // Helper function to close sidebar
    function closeSidebar() {
        sidebar.classList.remove('open');
        mainContent.classList.remove('sidebar-open');
        toggleTab.style.opacity = '1';
        toggleTab.style.pointerEvents = 'auto';
    }
}

/**
 * Initialize layout option buttons
 */
function initializeLayoutOptions() {
    const grid = document.getElementById('kpiCardsGrid');
    const layoutBtns = document.querySelectorAll('.kpi-layout-option');

    if (!grid || layoutBtns.length === 0) {
        console.warn('Layout elements not found');
        return;
    }

    layoutBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const cols = this.getAttribute('data-cols');

            // Update active state
            layoutBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Update grid columns
            grid.setAttribute('data-cols', cols);

            // Save preference to localStorage
            localStorage.setItem('kpi-layout-cols', cols);
        });
    });

    // Load saved preference
    const savedCols = localStorage.getItem('kpi-layout-cols');
    if (savedCols) {
        const btn = document.querySelector(`.kpi-layout-option[data-cols="${savedCols}"]`);
        if (btn) {
            // Trigger click to apply saved layout
            btn.click();
        }
    }
}
