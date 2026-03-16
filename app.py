from flask import Flask, render_template, request, redirect, session, url_for, flash
import uuid
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Local in-memory state for initial development phase
state = {
    'patients': {},
    'doctors': {
        'doc1': {
            'DoctorID': 'doc1',
            'Name': 'Dr. Alice',
            'Email': 'alice@clinic.com',
            'Password': 'password',
            'Specialty': 'General'
        },
        'doc2': {
            'DoctorID': 'doc2',
            'Name': 'Dr. Bob',
            'Email': 'bob@clinic.com',
            'Password': 'password',
            'Specialty': 'Pediatrics'
        }
    },
    'appointments': {},
    'diagnoses': {}
}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('Please complete all fields.', 'error')
            return redirect(url_for('register'))

        # check email already used
        for patient in state['patients'].values():
            if patient['Email'] == email:
                flash('Email already registered. Login instead.', 'error')
                return redirect(url_for('register'))

        patient_id = str(uuid.uuid4())
        state['patients'][patient_id] = {
            'PatientID': patient_id,
            'Name': name,
            'Email': email,
            'Password': password,
            'MedicalHistory': []
        }
        flash('Registration successful. Login now.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if role == 'patient':
            for patient in state['patients'].values():
                if patient['Email'] == email and patient['Password'] == password:
                    session['user_role'] = 'patient'
                    session['user_id'] = patient['PatientID']
                    return redirect(url_for('dashboard'))
            flash('Invalid patient credentials.', 'error')
        elif role == 'doctor':
            for doctor in state['doctors'].values():
                if doctor['Email'] == email and doctor['Password'] == password:
                    session['user_role'] = 'doctor'
                    session['user_id'] = doctor['DoctorID']
                    return redirect(url_for('dashboard'))
            flash('Invalid doctor credentials.', 'error')
        else:
            flash('Please select a role.', 'error')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    role = session.get('user_role')
    user_id = session.get('user_id')
    if not role or not user_id:
        return redirect(url_for('login'))

    if role == 'patient':
        patient = state['patients'].get(user_id)
        if not patient:
            return redirect(url_for('login'))
        upcoming = [a for a in state['appointments'].values() if a['PatientID'] == user_id]
        return render_template('dashboard_patient.html', patient=patient, appointments=upcoming)

    doctor = state['doctors'].get(user_id)
    if not doctor:
        return redirect(url_for('login'))
    doctor_appointments = [a for a in state['appointments'].values() if a['DoctorID'] == user_id]
    return render_template('dashboard_doctor.html', doctor=doctor, appointments=doctor_appointments)


@app.route('/book', methods=['GET', 'POST'])
def book():
    if session.get('user_role') != 'patient':
        flash('Only patients can book appointments.', 'error')
        return redirect(url_for('dashboard'))

    user_id = session.get('user_id')
    patient = state['patients'].get(user_id)
    if not patient:
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        reason = request.form.get('reason', '').strip()

        if not doctor_id or not date:
            flash('Please select doctor and date.', 'error')
            return redirect(url_for('book'))

        appointment_id = str(uuid.uuid4())
        state['appointments'][appointment_id] = {
            'AppointmentID': appointment_id,
            'PatientID': user_id,
            'DoctorID': doctor_id,
            'Date': date,
            'Reason': reason,
            'Status': 'Pending'
        }

        flash('Appointment booked successfully.', 'success')
        return redirect(url_for('dashboard'))

    doctors = list(state['doctors'].values())
    return render_template('book.html', patient=patient, doctors=doctors)


@app.route('/diagnosis', methods=['GET', 'POST'])
def diagnosis():
    if session.get('user_role') != 'doctor':
        flash('Only doctors can submit diagnosis.', 'error')
        return redirect(url_for('dashboard'))

    user_id = session.get('user_id')
    doctor = state['doctors'].get(user_id)
    if not doctor:
        return redirect(url_for('login'))

    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        notes = request.form.get('notes', '').strip()

        if not appointment_id or not notes:
            flash('Please choose appointment and enter notes.', 'error')
            return redirect(url_for('diagnosis'))

        appointment = state['appointments'].get(appointment_id)
        if not appointment:
            flash('Appointment not found.', 'error')
            return redirect(url_for('diagnosis'))

        appointment['Status'] = 'Completed'
        diag_id = str(uuid.uuid4())
        state['diagnoses'][diag_id] = {
            'DiagnosisID': diag_id,
            'AppointmentID': appointment_id,
            'PatientID': appointment['PatientID'],
            'DoctorID': user_id,
            'Notes': notes,
            'Date': appointment['Date']
        }

        patient = state['patients'].get(appointment['PatientID'])
        if patient is not None:
            patient['MedicalHistory'].append({
                'Date': appointment['Date'],
                'Doctor': doctor['Name'],
                'Notes': notes,
                'Reason': appointment.get('Reason', '')
            })

        flash('Diagnosis saved and history updated.', 'success')
        return redirect(url_for('dashboard'))

    doctor_appointments = [a for a in state['appointments'].values() if a['DoctorID'] == user_id]
    return render_template('diagnosis.html', doctor=doctor, appointments=doctor_appointments)


@app.route('/history')
def history():
    if session.get('user_role') != 'patient':
        flash('Only patients can view medical history.', 'error')
        return redirect(url_for('dashboard'))

    user_id = session.get('user_id')
    patient = state['patients'].get(user_id)
    if not patient:
        return redirect(url_for('login'))

    return render_template('history.html', patient=patient)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
