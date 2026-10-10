class Account {
  const Account({required this.id, required this.email, required this.displayName, required this.role});

  final int id;
  final String email;
  final String displayName;
  final String role;

  factory Account.fromJson(Map<String, dynamic> json) => Account(
        id: json['id'] as int,
        email: json['email'] as String,
        displayName: json['display_name'] as String,
        role: json['role'] as String,
      );
}

class Patient {
  const Patient({required this.id, required this.name});

  final int id;
  final String name;

  factory Patient.fromJson(Map<String, dynamic> json) => Patient(
        id: json['id'] as int,
        name: json['name'] as String,
      );
}

class MedicationSchedule {
  const MedicationSchedule({
    required this.id,
    required this.patientId,
    required this.medicationName,
    required this.slot,
    required this.time,
    required this.active,
  });

  final int id;
  final int patientId;
  final String medicationName;
  final int slot;
  final String time;
  final bool active;

  factory MedicationSchedule.fromJson(Map<String, dynamic> json) => MedicationSchedule(
        id: json['id'] as int,
        patientId: json['care_receiver_id'] as int,
        medicationName: json['medication_name'] as String,
        slot: json['compartment'] as int,
        time: json['time'] as String,
        active: json['is_active'] as bool,
      );
}
