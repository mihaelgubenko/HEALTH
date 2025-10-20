// Улучшенная форма записи на прием
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('appointmentForm');
    const steps = document.querySelectorAll('.form-step');
    const progressBar = document.querySelector('.progress-bar');
    const nextBtns = document.querySelectorAll('.btn-next');
    const prevBtns = document.querySelectorAll('.btn-prev');
    let currentStep = 0;

    // Инициализация
    if (steps.length > 0) {
        showStep(currentStep);
        updateProgressBar();
    }

    // Обработчики кнопок "Далее"
    nextBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            if (validateStep(currentStep)) {
                currentStep++;
                showStep(currentStep);
                updateProgressBar();
            }
        });
    });

    // Обработчики кнопок "Назад"
    prevBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            currentStep--;
            showStep(currentStep);
            updateProgressBar();
        });
    });

    // Показать определенный шаг
    function showStep(step) {
        steps.forEach((stepEl, index) => {
            stepEl.style.display = index === step ? 'block' : 'none';
        });
    }

    // Обновить прогресс-бар
    function updateProgressBar() {
        if (progressBar) {
            const progress = ((currentStep + 1) / steps.length) * 100;
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
        }
    }

    // Валидация шага
    function validateStep(step) {
        const currentStepEl = steps[step];
        const requiredFields = currentStepEl.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                showFieldError(field, 'Это поле обязательно для заполнения');
                isValid = false;
            } else {
                clearFieldError(field);
            }
        });

        return isValid;
    }

    // Показать ошибку поля
    function showFieldError(field, message) {
        clearFieldError(field);
        field.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    // Очистить ошибку поля
    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    // Валидация телефона в реальном времени
    const phoneField = document.getElementById('id_phone');
    if (phoneField) {
        phoneField.addEventListener('input', function() {
            const phone = this.value.replace(/\D/g, '');
            
            if (phone.length > 0) {
                // Форматирование израильского номера
                if (phone.startsWith('972') || phone.startsWith('0')) {
                    let formatted = phone;
                    if (phone.startsWith('0')) {
                        formatted = '972' + phone.substring(1);
                    }
                    this.value = '+' + formatted;
                } else if (!phone.startsWith('972')) {
                    this.value = '+972' + phone;
                }
            }
        });
    }

    // Обновление специалистов при выборе услуги
    const serviceField = document.getElementById('id_service');
    const specialistField = document.getElementById('id_specialist');
    
    if (serviceField && specialistField) {
        serviceField.addEventListener('change', function() {
            const serviceId = this.value;
            
            if (serviceId) {
                // Показать загрузку
                specialistField.innerHTML = '<option value="">Загрузка...</option>';
                specialistField.disabled = true;
                
                // AJAX запрос для получения специалистов
                fetch(`/api/specialists/?service_id=${serviceId}`)
                    .then(response => response.json())
                    .then(data => {
                        specialistField.innerHTML = '<option value="">Выберите специалиста</option>';
                        
                        data.forEach(specialist => {
                            const option = document.createElement('option');
                            option.value = specialist.id;
                            option.textContent = `${specialist.name} - ${specialist.specialty}`;
                            specialistField.appendChild(option);
                        });
                        
                        specialistField.disabled = false;
                    })
                    .catch(error => {
                        console.error('Ошибка загрузки специалистов:', error);
                        specialistField.innerHTML = '<option value="">Ошибка загрузки</option>';
                        specialistField.disabled = false;
                    });
            } else {
                specialistField.innerHTML = '<option value="">Сначала выберите услугу</option>';
                specialistField.disabled = true;
            }
        });
    }

    // Анимация появления формы
    if (form) {
        form.style.opacity = '0';
        form.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            form.style.transition = 'all 0.5s ease';
            form.style.opacity = '1';
            form.style.transform = 'translateY(0)';
        }, 100);
    }

    // Подтверждение перед отправкой
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Подтвердите отправку заявки на запись к врачу.')) {
                e.preventDefault();
            }
        });
    }
});

// Утилиты для работы с датами
function formatDate(date) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
    };
    return date.toLocaleDateString('ru-RU', options);
}

function isWeekend(date) {
    const day = date.getDay();
    return day === 0 || day === 6; // Воскресенье или суббота
}

// Блокировка прошедших дат
document.addEventListener('DOMContentLoaded', function() {
    const dateField = document.getElementById('id_preferred_date');
    if (dateField) {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        dateField.min = tomorrow.toISOString().split('T')[0];
    }
});
