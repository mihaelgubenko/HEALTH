/**
 * AJAX валидация для админки Django
 * Обеспечивает валидацию в реальном времени для форм записей и пациентов
 */

(function($) {
    'use strict';

    // Конфигурация
    const CONFIG = {
        debounceDelay: 500,
        apiUrls: {
            validateAppointment: '/admin-api/validate-appointment/',
            getSlots: '/admin-api/get-slots/',
            checkConflicts: '/admin-api/check-conflicts/',
            validatePatient: '/admin-api/validate-patient/',
            patientSuggestions: '/admin-api/patient-suggestions/'
        },
        selectors: {
            appointmentForm: '.appointment-form, form[name="appointment"]',
            patientForm: '.patient-form, form[name="patient"]',
            nameField: '#id_name, input[name="name"]',
            phoneField: '#id_phone, input[name="phone"]',
            serviceField: '#id_service, select[name="service"]',
            specialistField: '#id_specialist, select[name="specialist"]',
            dateField: '#id_start_time_0, input[name="start_time_0"]',
            timeField: '#id_start_time_1, input[name="start_time_1"]',
            patientField: '#id_patient, select[name="patient"]'
        }
    };

    // Утилиты
    const Utils = {
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        getCsrfToken: function() {
            return $('[name=csrfmiddlewaretoken]').val() || 
                   document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                   '';
        },

        showValidationMessage: function(field, message, type = 'error') {
            const $field = $(field);
            const $container = $field.closest('.form-row, .field-box, .form-group');
            
            // Удаляем предыдущие сообщения
            $container.find('.validation-message').remove();
            
            if (message) {
                const cssClass = type === 'error' ? 'validation-error' : 
                               type === 'warning' ? 'validation-warning' : 'validation-info';
                
                const $message = $(`
                    <div class="validation-message ${cssClass}" style="
                        margin-top: 5px; 
                        padding: 8px 12px; 
                        border-radius: 4px; 
                        font-size: 13px;
                        ${type === 'error' ? 'background: #ffebee; color: #c62828; border: 1px solid #ef5350;' : ''}
                        ${type === 'warning' ? 'background: #fff3e0; color: #ef6c00; border: 1px solid #ff9800;' : ''}
                        ${type === 'info' ? 'background: #e3f2fd; color: #1565c0; border: 1px solid #2196f3;' : ''}
                    ">
                        ${message}
                    </div>
                `);
                
                $container.append($message);
                
                // Автоматически скрываем информационные сообщения через 5 секунд
                if (type === 'info') {
                    setTimeout(() => $message.fadeOut(), 5000);
                }
            }
        },

        showFieldError: function(field, error) {
            $(field).addClass('validation-error-field').css({
                'border-color': '#f44336',
                'box-shadow': '0 0 0 2px rgba(244, 67, 54, 0.2)'
            });
            this.showValidationMessage(field, error, 'error');
        },

        clearFieldError: function(field) {
            $(field).removeClass('validation-error-field').css({
                'border-color': '',
                'box-shadow': ''
            });
            this.showValidationMessage(field, '', 'error');
        },

        makeApiRequest: function(url, data, method = 'POST') {
            const requestData = {
                url: url,
                method: method,
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            };

            if (method === 'POST') {
                requestData.data = JSON.stringify(data);
            } else if (method === 'GET') {
                requestData.url += '?' + $.param(data);
            }

            return $.ajax(requestData);
        }
    };

    // Валидатор записей
    const AppointmentValidator = {
        init: function() {
            const $form = $(CONFIG.selectors.appointmentForm);
            if ($form.length === 0) return;

            this.bindEvents();
            this.initSlotUpdater();
        },

        bindEvents: function() {
            // Валидация при изменении полей
            const fieldsToValidate = [
                CONFIG.selectors.nameField,
                CONFIG.selectors.phoneField,
                CONFIG.selectors.serviceField,
                CONFIG.selectors.specialistField,
                CONFIG.selectors.dateField,
                CONFIG.selectors.timeField
            ];

            fieldsToValidate.forEach(selector => {
                $(document).on('change keyup', selector, 
                    Utils.debounce(this.validateForm.bind(this), CONFIG.debounceDelay)
                );
            });

            // Обновление слотов при изменении специалиста или даты
            $(document).on('change', CONFIG.selectors.specialistField + ', ' + CONFIG.selectors.dateField, 
                this.updateAvailableSlots.bind(this)
            );

            // Проверка конфликтов при изменении времени
            $(document).on('change', CONFIG.selectors.timeField, 
                Utils.debounce(this.checkTimeConflicts.bind(this), 300)
            );
        },

        validateForm: function() {
            const formData = this.getFormData();
            
            if (!formData.name && !formData.phone) {
                return; // Не валидируем пустую форму
            }

            Utils.makeApiRequest(CONFIG.apiUrls.validateAppointment, formData)
                .done(this.handleValidationResponse.bind(this))
                .fail(this.handleValidationError.bind(this));
        },

        getFormData: function() {
            return {
                name: $(CONFIG.selectors.nameField).val() || '',
                phone: $(CONFIG.selectors.phoneField).val() || '',
                service: $(CONFIG.selectors.serviceField + ' option:selected').text() || '',
                specialist: $(CONFIG.selectors.specialistField + ' option:selected').text() || '',
                date: $(CONFIG.selectors.dateField).val() || '',
                time: $(CONFIG.selectors.timeField).val() || '',
                appointment_id: this.getAppointmentId()
            };
        },

        getAppointmentId: function() {
            // Извлекаем ID записи из URL (для редактирования)
            const urlParts = window.location.pathname.split('/');
            const changeIndex = urlParts.indexOf('change');
            if (changeIndex > 0 && urlParts[changeIndex - 1]) {
                return parseInt(urlParts[changeIndex - 1]);
            }
            return null;
        },

        handleValidationResponse: function(response) {
            // Очищаем предыдущие ошибки
            this.clearAllErrors();

            if (response.is_valid) {
                this.showSuccessMessage();
            } else {
                this.showErrors(response.errors);
                this.showSuggestions(response.suggestions);
                this.showAlternatives(response.alternatives);
            }

            if (response.warnings && response.warnings.length > 0) {
                this.showWarnings(response.warnings);
            }
        },

        handleValidationError: function(xhr) {
            console.error('Validation error:', xhr);
            Utils.showValidationMessage(
                $(CONFIG.selectors.appointmentForm), 
                'Ошибка валидации. Попробуйте еще раз.', 
                'error'
            );
        },

        clearAllErrors: function() {
            const fields = [
                CONFIG.selectors.nameField,
                CONFIG.selectors.phoneField,
                CONFIG.selectors.serviceField,
                CONFIG.selectors.specialistField,
                CONFIG.selectors.dateField,
                CONFIG.selectors.timeField
            ];

            fields.forEach(selector => {
                Utils.clearFieldError(selector);
            });
        },

        showErrors: function(errors) {
            errors.forEach(error => {
                if (error.includes('Имя:')) {
                    Utils.showFieldError(CONFIG.selectors.nameField, error);
                } else if (error.includes('Телефон:')) {
                    Utils.showFieldError(CONFIG.selectors.phoneField, error);
                } else if (error.includes('Услуга:')) {
                    Utils.showFieldError(CONFIG.selectors.serviceField, error);
                } else if (error.includes('Специалист:')) {
                    Utils.showFieldError(CONFIG.selectors.specialistField, error);
                } else if (error.includes('Дата:')) {
                    Utils.showFieldError(CONFIG.selectors.dateField, error);
                } else if (error.includes('Время:')) {
                    Utils.showFieldError(CONFIG.selectors.timeField, error);
                } else {
                    // Общая ошибка
                    Utils.showValidationMessage(
                        $(CONFIG.selectors.appointmentForm), 
                        error, 
                        'error'
                    );
                }
            });
        },

        showWarnings: function(warnings) {
            warnings.forEach(warning => {
                Utils.showValidationMessage(
                    $(CONFIG.selectors.appointmentForm), 
                    warning, 
                    'warning'
                );
            });
        },

        showSuggestions: function(suggestions) {
            if (suggestions.length > 0) {
                const message = '💡 Предложения: ' + suggestions.join(', ');
                Utils.showValidationMessage(
                    $(CONFIG.selectors.timeField), 
                    message, 
                    'info'
                );
            }
        },

        showAlternatives: function(alternatives) {
            if (alternatives.length > 0) {
                let message = '📅 Альтернативные даты:\n';
                alternatives.slice(0, 3).forEach(alt => {
                    message += `• ${alt.date_str} в ${alt.time}\n`;
                });
                
                Utils.showValidationMessage(
                    $(CONFIG.selectors.dateField), 
                    message.replace(/\n/g, '<br>'), 
                    'info'
                );
            }
        },

        showSuccessMessage: function() {
            Utils.showValidationMessage(
                $(CONFIG.selectors.appointmentForm), 
                '✅ Все данные корректны!', 
                'info'
            );
        },

        updateAvailableSlots: function() {
            const specialistId = $(CONFIG.selectors.specialistField).val();
            const date = $(CONFIG.selectors.dateField).val();
            const serviceId = $(CONFIG.selectors.serviceField).val();

            if (!specialistId || !date) return;

            const data = {
                specialist_id: specialistId,
                date: date,
                service_id: serviceId
            };

            Utils.makeApiRequest(CONFIG.apiUrls.getSlots, data)
                .done(this.handleSlotsResponse.bind(this))
                .fail(function(xhr) {
                    console.error('Error getting slots:', xhr);
                });
        },

        handleSlotsResponse: function(response) {
            if (response.success) {
                this.updateTimeField(response.slots);
                
                if (response.slots.length === 0) {
                    Utils.showValidationMessage(
                        $(CONFIG.selectors.timeField), 
                        'На выбранную дату нет доступных слотов', 
                        'warning'
                    );
                } else {
                    Utils.showValidationMessage(
                        $(CONFIG.selectors.timeField), 
                        `Доступно слотов: ${response.slots.length}`, 
                        'info'
                    );
                }
            }
        },

        updateTimeField: function(slots) {
            const $timeField = $(CONFIG.selectors.timeField);
            const currentValue = $timeField.val();
            
            // Если поле времени - это select
            if ($timeField.is('select')) {
                $timeField.empty().append('<option value="">Выберите время</option>');
                
                slots.forEach(slot => {
                    const option = $(`<option value="${slot.time}">${slot.time}</option>`);
                    if (slot.time === currentValue) {
                        option.prop('selected', true);
                    }
                    $timeField.append(option);
                });
            }
            // Если поле времени - это input, добавляем datalist
            else if ($timeField.is('input')) {
                let $datalist = $('#time-suggestions');
                if ($datalist.length === 0) {
                    $datalist = $('<datalist id="time-suggestions"></datalist>');
                    $timeField.after($datalist);
                    $timeField.attr('list', 'time-suggestions');
                }
                
                $datalist.empty();
                slots.forEach(slot => {
                    $datalist.append(`<option value="${slot.time}">`);
                });
            }
        },

        checkTimeConflicts: function() {
            const formData = this.getFormData();
            
            if (!formData.specialist || !formData.date || !formData.time) {
                return;
            }

            // Создаем datetime объекты
            const startDateTime = new Date(`${formData.date}T${formData.time}:00`);
            const endDateTime = new Date(startDateTime.getTime() + 60 * 60 * 1000); // +1 час

            const data = {
                specialist_id: $(CONFIG.selectors.specialistField).val(),
                start_datetime: startDateTime.toISOString(),
                end_datetime: endDateTime.toISOString(),
                appointment_id: this.getAppointmentId()
            };

            Utils.makeApiRequest(CONFIG.apiUrls.checkConflicts, data)
                .done(this.handleConflictsResponse.bind(this))
                .fail(function(xhr) {
                    console.error('Error checking conflicts:', xhr);
                });
        },

        handleConflictsResponse: function(response) {
            if (response.success && response.has_conflicts) {
                const message = '⚠️ Конфликт времени: ' + response.conflicts.join('; ');
                Utils.showFieldError(CONFIG.selectors.timeField, message);
            }
        },

        initSlotUpdater: function() {
            // Автоматически обновляем слоты при загрузке страницы
            if ($(CONFIG.selectors.specialistField).val() && $(CONFIG.selectors.dateField).val()) {
                this.updateAvailableSlots();
            }
        }
    };

    // Валидатор пациентов
    const PatientValidator = {
        init: function() {
            const $form = $(CONFIG.selectors.patientForm);
            if ($form.length === 0) return;

            this.bindEvents();
        },

        bindEvents: function() {
            $(document).on('change keyup', CONFIG.selectors.nameField + ', ' + CONFIG.selectors.phoneField, 
                Utils.debounce(this.validatePatient.bind(this), CONFIG.debounceDelay)
            );
        },

        validatePatient: function() {
            const data = {
                name: $(CONFIG.selectors.nameField).val() || '',
                phone: $(CONFIG.selectors.phoneField).val() || '',
                patient_id: this.getPatientId()
            };

            if (!data.name && !data.phone) return;

            Utils.makeApiRequest(CONFIG.apiUrls.validatePatient, data)
                .done(this.handleValidationResponse.bind(this))
                .fail(function(xhr) {
                    console.error('Patient validation error:', xhr);
                });
        },

        getPatientId: function() {
            const urlParts = window.location.pathname.split('/');
            const changeIndex = urlParts.indexOf('change');
            if (changeIndex > 0 && urlParts[changeIndex - 1]) {
                return parseInt(urlParts[changeIndex - 1]);
            }
            return null;
        },

        handleValidationResponse: function(response) {
            // Очищаем предыдущие ошибки
            Utils.clearFieldError(CONFIG.selectors.nameField);
            Utils.clearFieldError(CONFIG.selectors.phoneField);

            if (!response.is_valid) {
                response.errors.forEach(error => {
                    if (error.includes('Имя:')) {
                        Utils.showFieldError(CONFIG.selectors.nameField, error);
                    } else if (error.includes('Телефон:')) {
                        Utils.showFieldError(CONFIG.selectors.phoneField, error);
                    }
                });
            }

            if (response.warnings && response.warnings.length > 0) {
                response.warnings.forEach(warning => {
                    if (warning.includes('телефон')) {
                        Utils.showValidationMessage(CONFIG.selectors.phoneField, warning, 'warning');
                    } else {
                        Utils.showValidationMessage(CONFIG.selectors.nameField, warning, 'warning');
                    }
                });
            }

            if (response.suggestions && response.suggestions.length > 0) {
                const message = '💡 ' + response.suggestions.join('; ');
                Utils.showValidationMessage(CONFIG.selectors.phoneField, message, 'info');
            }
        }
    };

    // Автокомплит для пациентов
    const PatientAutocomplete = {
        init: function() {
            const $patientField = $(CONFIG.selectors.patientField);
            if ($patientField.length === 0) return;

            this.initAutocomplete($patientField);
        },

        initAutocomplete: function($field) {
            // Создаем поле для поиска
            const $searchInput = $('<input type="text" placeholder="Поиск пациента..." style="width: 100%; margin-bottom: 5px;">');
            $field.before($searchInput);

            $searchInput.on('input', Utils.debounce(function() {
                const query = $(this).val();
                if (query.length >= 2) {
                    PatientAutocomplete.searchPatients(query, $field);
                }
            }, 300));
        },

        searchPatients: function(query, $selectField) {
            Utils.makeApiRequest(CONFIG.apiUrls.patientSuggestions, { q: query }, 'GET')
                .done(function(response) {
                    PatientAutocomplete.updatePatientOptions(response.suggestions, $selectField);
                })
                .fail(function(xhr) {
                    console.error('Patient search error:', xhr);
                });
        },

        updatePatientOptions: function(suggestions, $selectField) {
            const currentValue = $selectField.val();
            
            // Сохраняем первую опцию (обычно "--------")
            const $firstOption = $selectField.find('option:first');
            $selectField.empty().append($firstOption);

            suggestions.forEach(patient => {
                const option = $(`<option value="${patient.id}">${patient.label}</option>`);
                if (patient.id == currentValue) {
                    option.prop('selected', true);
                }
                $selectField.append(option);
            });
        }
    };

    // Инициализация при загрузке DOM
    $(document).ready(function() {
        AppointmentValidator.init();
        PatientValidator.init();
        PatientAutocomplete.init();

        // Добавляем стили для валидации
        if ($('#admin-validation-styles').length === 0) {
            $('head').append(`
                <style id="admin-validation-styles">
                    .validation-error-field {
                        animation: shake 0.5s ease-in-out;
                    }
                    
                    @keyframes shake {
                        0%, 100% { transform: translateX(0); }
                        25% { transform: translateX(-5px); }
                        75% { transform: translateX(5px); }
                    }
                    
                    .validation-message {
                        animation: fadeIn 0.3s ease-in-out;
                    }
                    
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(-10px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                </style>
            `);
        }
    });

})(django.jQuery || jQuery);
