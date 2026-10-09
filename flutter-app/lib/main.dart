import 'package:flutter/material.dart';

import 'api/smart_pill_api.dart';
import 'models.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

void main() => runApp(const SmartPillBoxApp());

class SmartPillBoxApp extends StatefulWidget {
  const SmartPillBoxApp({super.key});

  @override
  State<SmartPillBoxApp> createState() => _SmartPillBoxAppState();
}

class _SmartPillBoxAppState extends State<SmartPillBoxApp> {
  final _api = SmartPillApi();
  Account? _account;
  List<Patient> _patients = [];
  List<MedicationSchedule> _schedules = [];

  Future<void> _login(String email, String password) async {
    await _api.login(email, password);
    final account = await _api.me();
    if (account.role != 'caregiver') {
      _api.clearSession();
      throw const ApiException('Ứng dụng này dành cho tài khoản người thân.');
    }
    final patients = await _api.patients();
    final schedules = await _api.schedules();
    if (!mounted) return;
    setState(() {
      _account = account;
      _patients = patients;
      _schedules = schedules;
    });
  }

  Future<void> _refreshSchedules() async {
    final schedules = await _api.schedules();
    if (mounted) setState(() => _schedules = schedules);
  }

  void _logout() => setState(() {
        _api.clearSession();
        _account = null;
        _patients = [];
        _schedules = [];
      });

  @override
  void dispose() {
    _api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Smart Pill Box',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF315C49), brightness: Brightness.light),
          scaffoldBackgroundColor: const Color(0xFFF5F4EE),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Color(0xFFE4E5DD))),
          ),
        ),
        home: _account == null
            ? LoginScreen(onLogin: _login)
            : HomeScreen(
                account: _account!,
                patients: _patients,
                schedules: _schedules,
                onCreateSchedule: (values) async {
                  await _api.createSchedule(
                    patientId: values['patient_id'] as int,
                    medicationName: values['medication_name'] as String,
                    slot: values['slot'] as int,
                    time: values['time'] as String,
                  );
                  await _refreshSchedules();
                },
                onLogout: _logout,
              ),
      );
}
