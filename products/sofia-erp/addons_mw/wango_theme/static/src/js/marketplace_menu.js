/** @odoo-module **/

document.addEventListener('DOMContentLoaded', () => {
    const openSidebar = (ev) => {
        ev.preventDefault();
        const sidebar = document.getElementById('wbl_sidebar');
        const overlay = document.getElementById('wbl_sidebar_overlay');
        if (sidebar) sidebar.classList.add('wbl-sidebar-open');
        if (overlay) {
            overlay.style.display = 'block';
            overlay.classList.add('wbl-sidebar-open');
        }
        document.body.style.overflow = 'hidden';
    };

    const closeSidebar = (ev) => {
        ev.preventDefault();
        const sidebar = document.getElementById('wbl_sidebar');
        const overlay = document.getElementById('wbl_sidebar_overlay');
        if (sidebar) sidebar.classList.remove('wbl-sidebar-open');
        if (overlay) {
            overlay.classList.remove('wbl-sidebar-open');
            overlay.style.display = 'none';
        }
        document.body.style.overflow = '';
    };

    document.addEventListener('click', (ev) => {
        if (ev.target.closest('.wbl-menu-btn, .wbl-header-menu-btn')) {
            openSidebar(ev);
        } else if (ev.target.closest('#wbl_close_sidebar, #wbl_sidebar_overlay')) {
            closeSidebar(ev);
        } else {
            const item = ev.target.closest('.wbl-mega-menu-item');
            if (item) activateCategoryTab(item);
        }
    });

    document.addEventListener('mouseover', (ev) => {
        const item = ev.target.closest('.wbl-mega-menu-item');
        if (item) activateCategoryTab(item);
    });

    function activateCategoryTab(item) {
        const catId = item.getAttribute('data-category-id');
        document.querySelectorAll('.wbl-mega-menu-item').forEach((el) => el.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.wbl-category-panel').forEach((panel) => {
            panel.classList.remove('active');
            panel.style.display = 'none';
        });
        const target = document.getElementById('wbl-category-panel-' + catId);
        if (target) {
            target.classList.add('active');
            target.style.display = 'block';
        }
    }
});
