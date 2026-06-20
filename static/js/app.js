document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    document.querySelectorAll('input[type="range"], input[name="porcentaje_avance"]').forEach((input) => {
        const update = () => {
            const value = input.value || 0;

            input.style.setProperty('--value', `${value}%`);

            const circle = document.querySelector('.large-circle span');

            if (circle && input.name === 'porcentaje_avance') {
                circle.textContent = `${value}%`;
            }
        };

        input.addEventListener('input', update);
        update();
    });

    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach((input) => {
        input.addEventListener('change', () => {
            const preview = document.getElementById('imagePreview');

            if (!preview || !input.files || !input.files[0]) {
                return;
            }

            preview.innerHTML = '';

            const img = document.createElement('img');
            img.src = URL.createObjectURL(input.files[0]);
            img.alt = 'Vista previa de evidencia';

            preview.appendChild(img);
        });
    });
});