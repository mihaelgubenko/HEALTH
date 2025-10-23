from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Service, Specialist, FAQ, Patient, Appointment
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Загружает начальные данные (Каталог А)'

    def handle(self, *args, **options):
        self.stdout.write('Загрузка начальных данных...')

        # Создание услуг (Каталог А - Израиль)
        services_data = [
            {
                'name': 'Консультация реабилитолога',
                'description': 'Включает комплексное обследование пациента, сбор анамнеза, физический осмотр, оценку двигательных функций и разработку индивидуальной программы реабилитации. На консультации реабилитолог объясняет суть травмы или болезни, определяет реабилитационный прогноз и составляет план восстановительных мероприятий, который может включать ЛФК, физиотерапию, массаж и другие методики.',
                'price': 80,
                'currency': '₪',
                'duration': 20,
                'catalog': 'A'
            },
            {
                'name': 'Консультация нутрициолога',
                'description': 'Включает первичный сбор информации (анкета о здоровье и питании, анализ текущего рациона, обсуждение целей), анализ данных (изучение анамнеза, при необходимости — назначение анализов или биоимпедансный анализ тела), разработку индивидуального плана питания (персональные рекомендации по рациону, режима питания, добавкам) и поддержку и контроль (коррекция плана, ответы на вопросы, помощь в формировании полезных привычек).',
                'price': 450,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A'
            },
            {
                'name': 'Консультация остеопата',
                'description': 'Включает сбор анамнеза (расспрос о симптомах, проблемах со здоровьем, перенесенных травмах и заболеваниях), диагностику (визуальный осмотр, пальпация, определение ограничений подвижности тканей, мышц, костей и связок) и план лечения (описание техник, которые будут использоваться, и прогноз результата).',
                'price': 80,
                'currency': '₪',
                'duration': 20,
                'catalog': 'A'
            },
            {
                'name': 'Лечебный массаж для мужчин (классический шведский)',
                'description': 'Классический шведский массаж для мужчин и парней-подростков. Длительность 50-60 минут.',
                'price': 250,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A'
            },
            {
                'name': 'Лечебный массаж для женщин (классический шведский)',
                'description': 'Классический шведский массаж для женщин, девушек-подростков и детей. Длительность 50-60 минут.',
                'price': 250,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A'
            },
            {
                'name': 'Массаж грудным детям',
                'description': 'Специальный массаж для грудных детей. Длительность 20-30 минут.',
                'price': 70,
                'currency': '₪',
                'duration': 30,
                'catalog': 'A'
            },
            {
                'name': 'Массаж беременным (от 5 месяцев)',
                'description': 'Специальный массаж для беременных женщин от 5 месяцев. Длительность 30-40 минут.',
                'price': 180,
                'currency': '₪',
                'duration': 40,
                'catalog': 'A'
            },
            {
                'name': 'Кинезиотейпирование',
                'description': 'Применяется для профилактики и реабилитации травм мышц, связок и суставов, снижения болей, отеков и улучшения кровообращения, а также в спорте для предотвращения травм и ускорения восстановления.',
                'price': 50,
                'currency': '₪',
                'duration': 30,
                'catalog': 'A'
            },
            {
                'name': 'Диагностика организма биорезонансным сканированием (базовая)',
                'description': 'Современная диагностика для тех, кто хочет понять, что происходит в организме — уже сегодня. Без боли, без уколов, без облучения. Полная распечатка результата без эпикриза.',
                'price': 300,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A'
            },
            {
                'name': 'Диагностика организма биорезонансным сканированием (расширенная)',
                'description': 'Современная диагностика с выявлением проблем, эпикризом и рекомендациями.',
                'price': 750,
                'currency': '₪',
                'duration': 90,
                'catalog': 'A'
            },
            {
                'name': 'Массаж детский',
                'description': 'Детский массаж для детей. Длительность 40-50 минут.',
                'price': 150,
                'currency': '₪',
                'duration': 50,
                'catalog': 'A'
            },
            {
                'name': 'Массаж после родов',
                'description': 'Массаж после родов от 1 месяца. Длительность 50-60 минут.',
                'price': 250,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A'
            },
            {
                'name': 'Диагностика организма биорезонансным сканированием (VIP)',
                'description': 'Диагностика организма биорезонансным сканированием - пакет VIP.',
                'price': 5500,
                'currency': '₪',
                'duration': 120,
                'catalog': 'A'
            },
            {
                'name': 'Подбор комплекса упражнений',
                'description': 'Подбор и демонстрация комплекса упражнений для реабилитации после травм, после родов, удаления гипоксии и др.',
                'price': 100,
                'currency': '₪',
                'duration': 45,
                'catalog': 'A'
            }
        ]

        for service_data in services_data:
            service, created = Service.objects.get_or_create(
                name=service_data['name'],
                defaults=service_data
            )
            if created:
                self.stdout.write(f'Создана услуга: {service.name}')
            else:
                self.stdout.write(f'Услуга уже существует: {service.name}')

        # Создание специалистов
        specialists_data = [
            {
                'name': 'Екатерина',
                'specialty': 'Врач-реабилитолог, врач спортивной медицины, остеопат',
                'description': 'Врач-реабилитолог, врач спортивной медицины, остеопат. Стаж работы с 2010 года (15+ лет). Специализируется на травмах и заболеваниях ОДА, восстановлении после операций, реабилитации спортсменов, онкореабилитации, детской реабилитации (включая РАС и ДЦП), реабилитации во время беременности и после родов. Применяет остеопатию, мануальную терапию, лечебный массаж, аппаратную физиотерапию, кинезиотейпирование.',
                'working_hours': {
                    'monday': {'start': '10:00', 'end': '19:00'},
                    'tuesday': {'start': '10:00', 'end': '19:00'},
                    'wednesday': {'start': '10:00', 'end': '19:00'},
                    'thursday': {'start': '10:00', 'end': '19:00'},
                    'sunday': {'start': '10:00', 'end': '19:00'}
                }
            },
            {
                'name': 'Римма',
                'specialty': 'Врач педиатр, врач нутрициолог',
                'description': 'Врач педиатр, врач нутрициолог. Кандидат медицинских наук. Опыт работы 40 лет. Обладает глубокими знаниями в области детского и взрослого здоровья, питания и доказательной медицины. Проводит комплексную оценку здоровья как ребенка, так и взрослого человека. Разрабатывает индивидуальный план питания с учетом потребностей и особенностей каждого, применяет научные знания для профилактики и лечения заболеваний, связанных с питанием.',
                'working_hours': {
                    'monday': {'start': '10:00', 'end': '19:00'},
                    'tuesday': {'start': '10:00', 'end': '19:00'},
                    'wednesday': {'start': '10:00', 'end': '19:00'},
                    'thursday': {'start': '10:00', 'end': '19:00'},
                    'sunday': {'start': '10:00', 'end': '19:00'}
                }
            },
            {
                'name': 'Авраам',
                'specialty': 'Массажист',
                'description': 'Опытный массажист. Специализируется на мануальной терапии в вертебрологии, лечебном массаже (классический шведский, акупрессура и точечный, спортивный, детский, лечебный), акупунктуре, вакуумных банках и кинезиотейпировании. Работает с пациентами всех возрастных групп.',
                'working_hours': {
                    'monday': {'start': '10:00', 'end': '19:00'},
                    'tuesday': {'start': '10:00', 'end': '19:00'},
                    'wednesday': {'start': '10:00', 'end': '19:00'},
                    'thursday': {'start': '10:00', 'end': '19:00'},
                    'sunday': {'start': '10:00', 'end': '19:00'}
                }
            }
        ]

        for specialist_data in specialists_data:
            specialist, created = Specialist.objects.get_or_create(
                name=specialist_data['name'],
                defaults=specialist_data
            )
            if created:
                self.stdout.write(f'Создан специалист: {specialist.name}')
            else:
                self.stdout.write(f'Специалист уже существует: {specialist.name}')

        # Создание FAQ
        faq_data = [
            {
                'question': 'Какие у вас цены на услуги?',
                'answer': 'У нас гибкая система ценообразования. Консультация реабилитолога - 80₪, нутрициолога - 450₪, массаж - 250₪. Полный прайс-лист доступен на сайте.',
                'category': 'prices',
                'language': 'ru'
            },
            {
                'question': 'Где находится ваш центр?',
                'answer': 'Наш центр расположен в Израиле. Рамот Алеф. ул. Сулам Яков 1/3. Точный адрес и карту проезда вы получите при записи на прием.',
                'category': 'address',
                'language': 'ru'
            },
            {
                'question': 'Есть ли парковка?',
                'answer': 'Да, у нас есть удобная парковка для клиентов. Детали уточняйте при записи.',
                'category': 'parking',
                'language': 'ru'
            },
            {
                'question': 'Нужна ли подготовка к процедуре?',
                'answer': 'Для большинства процедур специальная подготовка не требуется. Индивидуальные рекомендации вы получите при записи.',
                'category': 'preparation',
                'language': 'ru'
            }
        ]

        for faq_item in faq_data:
            faq, created = FAQ.objects.get_or_create(
                question=faq_item['question'],
                defaults=faq_item
            )
            if created:
                self.stdout.write(f'Создан FAQ: {faq.question[:50]}...')
            else:
                self.stdout.write(f'FAQ уже существует: {faq.question[:50]}...')

        # Создание тестовых пациентов
        test_patients = [
            {'name': 'Михаил Иванов', 'phone': '+972504611186', 'email': 'mikhail@example.com'},
            {'name': 'Анна Петрова', 'phone': '+972526784512', 'email': 'anna@example.com'},
            {'name': 'Давид Коэн', 'phone': '+972537894561', 'email': 'david@example.com'},
            {'name': 'Сара Леви', 'phone': '+972548965123', 'email': 'sara@example.com'},
            {'name': 'Алексей Смирнов', 'phone': '+972559632147', 'email': 'alexey@example.com'},
            {'name': 'Мария Розенберг', 'phone': '+972561234567', 'email': 'maria@example.com'},
            {'name': 'Игорь Волков', 'phone': '+972572345678', 'email': 'igor@example.com'},
            {'name': 'Ольга Гольдштейн', 'phone': '+972583456789', 'email': 'olga@example.com'},
        ]
        
        created_patients = []
        for patient_data in test_patients:
            patient, created = Patient.objects.get_or_create(
                phone=patient_data['phone'],
                defaults=patient_data
            )
            if created:
                self.stdout.write(f'Создан пациент: {patient.name}')
                created_patients.append(patient)
            else:
                created_patients.append(patient)
                self.stdout.write(f'Пациент уже существует: {patient.name}')
        
        # Создание тестовых записей (будущие записи)
        services = Service.objects.all()
        specialists = Specialist.objects.all()
        
        if services.exists() and specialists.exists() and created_patients:
            appointment_templates = [
                # Будущие записи на завтра и послезавтра
                {
                    'days_ahead': 1,
                    'times': ['09:00', '10:00', '11:00', '15:00', '16:00'],
                    'count': 3
                },
                {
                    'days_ahead': 2, 
                    'times': ['09:00', '12:00', '17:00', '18:00'],
                    'count': 2
                },
                {
                    'days_ahead': 3,
                    'times': ['10:00', '14:00', '16:00'],
                    'count': 2
                }
            ]
            
            created_appointments_count = 0
            for template in appointment_templates:
                for i in range(template['count']):
                    patient = random.choice(created_patients)
                    service = random.choice(services)
                    specialist = random.choice(specialists)
                    
                    # Выбираем время
                    appointment_time = random.choice(template['times'])
                    appointment_date = (timezone.now() + timedelta(days=template['days_ahead'])).date()
                    
                    # Создаем datetime
                    start_datetime = timezone.make_aware(
                        datetime.combine(appointment_date, datetime.strptime(appointment_time, '%H:%M').time())
                    )
                    end_datetime = start_datetime + timedelta(minutes=service.duration)
                    
                    # Проверяем конфликты
                    conflicts = Appointment.objects.filter(
                        specialist=specialist,
                        start_time__date=appointment_date,
                        start_time__time=start_datetime.time(),
                        status__in=['pending', 'confirmed']
                    )
                    
                    if not conflicts.exists():
                        appointment = Appointment.objects.create(
                            patient=patient,
                            service=service,
                            specialist=specialist,
                            start_time=start_datetime,
                            end_time=end_datetime,
                            status=random.choice(['pending', 'confirmed']),
                            channel='web',
                            notes=f'Тестовая запись для демонстрации'
                        )
                        created_appointments_count += 1
                        self.stdout.write(f'Создана запись: {patient.name} → {specialist.name} на {start_datetime.strftime("%d.%m.%Y %H:%M")}')
            
            self.stdout.write(f'Создано {created_appointments_count} тестовых записей')

        # Статистика
        self.stdout.write(f'\n--- СТАТИСТИКА ЗАГРУЖЕННЫХ ДАННЫХ ---')
        self.stdout.write(f'Услуг: {Service.objects.count()}')
        self.stdout.write(f'Специалистов: {Specialist.objects.count()}') 
        self.stdout.write(f'FAQ: {FAQ.objects.count()}')
        self.stdout.write(f'Пациентов: {Patient.objects.count()}')
        self.stdout.write(f'Записей: {Appointment.objects.count()}')

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Начальные и тестовые данные успешно загружены!')
        )
