document.addEventListener('DOMContentLoaded', function() {
    // Jadvalda hover effekti
    const tableRows = document.querySelectorAll('.data-table tbody tr');

    tableRows.forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.classList.add('drivers-table__row--hover');
        });
        row.addEventListener('mouseleave', () => {
            row.classList.remove('drivers-table__row--hover');
        });
    });

    // Delete tugmasi bosilganda tasdiqlash modal chiqishi
    const deleteForms = document.querySelectorAll('.delete-form');

    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            Swal.fire({
                title: 'Are you sure?',
                text: "You won't be able to revert this!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#6a00f4',
                cancelButtonColor: '#e74c3c',
                confirmButtonText: 'Yes, delete it!'
            }).then((result) => {
                if (result.isConfirmed) {
                    form.submit();
                }
            })
        });
    });
});