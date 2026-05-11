document.addEventListener('DOMContentLoaded', function() {
    var csrfToken = document.querySelector('input[name="csrf_token"]');
    if (!csrfToken) return;
    var token = csrfToken.value;

    // --- Quick Add Driver ---
    var saveDriverBtn = document.getElementById('saveDriverBtn');
    if (saveDriverBtn) {
        saveDriverBtn.addEventListener('click', function() {
            var alertEl = document.getElementById('driverModalAlert');
            alertEl.classList.add('d-none');

            var payload = {
                first_name: document.getElementById('drv_first_name').value,
                last_name: document.getElementById('drv_last_name').value,
                username: document.getElementById('drv_username').value,
                email: document.getElementById('drv_email').value,
                password: document.getElementById('drv_password').value,
                employee_number: document.getElementById('drv_employee_number').value,
                role: 'standard',
                csrf_token: token
            };

            fetch('/api/drivers', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(function(resp) { return resp.json().then(function(data) { return {ok: resp.ok, data: data}; }); })
            .then(function(result) {
                if (!result.ok) {
                    var msg = result.data.error || Object.values(result.data.errors || {}).join(', ') || 'An error occurred';
                    alertEl.textContent = msg;
                    alertEl.classList.remove('d-none');
                    return;
                }

                // Add new option to the driver select and select it
                var select = document.getElementById('primary_driver_user_id');
                if (select) {
                    var option = document.createElement('option');
                    option.value = result.data.id;
                    option.textContent = result.data.label;
                    option.selected = true;
                    select.appendChild(option);
                }

                // Close modal and reset form
                var modal = bootstrap.Modal.getInstance(document.getElementById('addDriverModal'));
                modal.hide();
                document.getElementById('drv_first_name').value = '';
                document.getElementById('drv_last_name').value = '';
                document.getElementById('drv_username').value = '';
                document.getElementById('drv_email').value = '';
                document.getElementById('drv_password').value = '';
                document.getElementById('drv_employee_number').value = '';
            })
            .catch(function() {
                alertEl.textContent = 'Network error. Please try again.';
                alertEl.classList.remove('d-none');
            });
        });
    }

    // --- Quick Add Location ---
    var saveLocationBtn = document.getElementById('saveLocationBtn');
    if (saveLocationBtn) {
        saveLocationBtn.addEventListener('click', function() {
            var alertEl = document.getElementById('locationModalAlert');
            alertEl.classList.add('d-none');

            var payload = {
                name: document.getElementById('loc_name').value,
                code: document.getElementById('loc_code').value,
                city: document.getElementById('loc_city').value,
                region: document.getElementById('loc_region').value,
                postcode: document.getElementById('loc_postcode').value,
                csrf_token: token
            };

            fetch('/api/locations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(function(resp) { return resp.json().then(function(data) { return {ok: resp.ok, data: data}; }); })
            .then(function(result) {
                if (!result.ok) {
                    var msg = result.data.error || Object.values(result.data.errors || {}).join(', ') || 'An error occurred';
                    alertEl.textContent = msg;
                    alertEl.classList.remove('d-none');
                    return;
                }

                // Add new option to the location select and select it
                var select = document.getElementById('location_id');
                if (select) {
                    var option = document.createElement('option');
                    option.value = result.data.id;
                    option.textContent = result.data.label;
                    option.selected = true;
                    select.appendChild(option);
                }

                // Close modal and reset form
                var modal = bootstrap.Modal.getInstance(document.getElementById('addLocationModal'));
                modal.hide();
                document.getElementById('loc_name').value = '';
                document.getElementById('loc_code').value = '';
                document.getElementById('loc_city').value = '';
                document.getElementById('loc_region').value = '';
                document.getElementById('loc_postcode').value = '';
            })
            .catch(function() {
                alertEl.textContent = 'Network error. Please try again.';
                alertEl.classList.remove('d-none');
            });
        });
    }
});
