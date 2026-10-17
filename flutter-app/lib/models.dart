class Account {
  const Account({
    required this.id,
    required this.email,
    required this.displayName,
    required this.role,
  });

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
        patientId: json['patient_id'] as int,
        medicationName: json['medication_name'] as String,
        slot: json['slot'] as int,
        time: json['time'] as String,
        active: json['active'] as bool,
      );

  MedicationSchedule copyWith({
    int? id,
    int? patientId,
    String? medicationName,
    int? slot,
    String? time,
    bool? active,
  }) =>
      MedicationSchedule(
        id: id ?? this.id,
        patientId: patientId ?? this.patientId,
        medicationName: medicationName ?? this.medicationName,
        slot: slot ?? this.slot,
        time: time ?? this.time,
        active: active ?? this.active,
      );
}

class DoseItem {
  const DoseItem({
    required this.id,
    required this.scheduleId,
    required this.scheduledAt,
    this.deadlineAt,
    this.confirmedAt,
    required this.status,
    this.reminderCount = 0,
  });

  final int id;
  final int scheduleId;
  final String scheduledAt;
  final String? deadlineAt;
  final String? confirmedAt;
  final String status;
  final int reminderCount;

  factory DoseItem.fromJson(Map<String, dynamic> json) => DoseItem(
        id: json['id'] as int,
        scheduleId: json['schedule_id'] as int,
        scheduledAt: json['scheduled_at'] as String,
        deadlineAt: json['deadline_at'] as String?,
        confirmedAt: json['confirmed_at'] as String?,
        status: (json['status'] ?? 'pending').toString(),
        reminderCount: (json['reminder_count'] as int?) ?? 0,
      );
}

class DeviceEventItem {
  const DeviceEventItem({
    required this.id,
    required this.eventUuid,
    required this.eventType,
    this.patientId,
    this.slot,
    this.occurrenceId,
    required this.payload,
    required this.timestamp,
    required this.createdAt,
  });

  final int id;
  final String eventUuid;
  final String eventType;
  final int? patientId;
  final int? slot;
  final int? occurrenceId;
  final Map<String, dynamic> payload;
  final String timestamp;
  final String createdAt;

  String get dateKey {
    final source = timestamp.isNotEmpty ? timestamp : createdAt;
    return source.length >= 10 ? source.substring(0, 10) : source;
  }

  factory DeviceEventItem.fromJson(Map<String, dynamic> json) {
    final rawPayload = json['payload'];
    final payload = rawPayload is Map<String, dynamic>
        ? rawPayload
        : <String, dynamic>{};
    final resolvedSlot = (json['slot'] as int?) ??
        (payload['slot'] as int?) ??
        (payload['compartment_id'] as int?);
    final createdAt = (json['created_at'] ?? '').toString();
    final timestamp = (json['occurred_at'] as String?) ??
        (payload['virtual_time'] as String?) ??
        createdAt;

    return DeviceEventItem(
      id: json['id'] as int,
      eventUuid: (json['event_uuid'] ?? '').toString(),
      eventType: (json['event_type'] ?? '').toString(),
      patientId: json['patient_id'] as int?,
      slot: resolvedSlot,
      occurrenceId: json['occurrence_id'] as int?,
      payload: payload,
      timestamp: timestamp,
      createdAt: createdAt,
    );
  }
}

class AlertItem {
  const AlertItem({
    required this.id,
    required this.patientId,
    this.occurrenceId,
    required this.kind,
    required this.status,
    required this.message,
    this.note,
    required this.createdAt,
    this.resolvedAt,
  });

  final int id;
  final int patientId;
  final int? occurrenceId;
  final String kind;
  final String status;
  final String message;
  final String? note;
  final String createdAt;
  final String? resolvedAt;

  bool get isPending => status == 'PENDING';

  factory AlertItem.fromJson(Map<String, dynamic> json) {
    final rawStatus = (json['status'] as String?)?.trim().toUpperCase();
    final resolvedAt = json['resolved_at'] as String?;
    final status = (rawStatus != null && rawStatus.isNotEmpty)
        ? rawStatus
        : (resolvedAt != null ? 'CHECKED' : 'PENDING');

    return AlertItem(
      id: json['id'] as int,
      patientId: json['patient_id'] as int,
      occurrenceId: json['occurrence_id'] as int?,
      kind: (json['kind'] ?? 'dose_overdue').toString(),
      status: status,
      message: (json['message'] ?? '').toString(),
      note: json['note'] as String?,
      createdAt: (json['created_at'] ?? '').toString(),
      resolvedAt: resolvedAt,
    );
  }
}
