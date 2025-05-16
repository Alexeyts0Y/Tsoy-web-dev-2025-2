'use strict'

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('deleteModal');
    
    modal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        const userId = button.getAttribute('data-user_id');
        const form = document.getElementById('deleteModalForm');
        form.action = `/lab4/users/${userId}/delete`;
    });
});