import 'package:flutter/material.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onLogin});

  final Future<void> Function(String email, String password) onLogin;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController(text: 'caregiver-a@example.test');
  final _password = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.onLogin(_email.text.trim(), _password.text);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    width: 62,
                    height: 62,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: colors.primaryContainer, borderRadius: BorderRadius.circular(20)),
                    child: Icon(Icons.medication_outlined, size: 32, color: colors.primary),
                  ),
                  const SizedBox(height: 30),
                  Text('SMART PILL BOX', style: TextStyle(color: colors.primary, fontSize: 12, letterSpacing: 2, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  const Text('Chăm sóc bắt đầu\ntừ một lịch nhỏ.', style: TextStyle(fontSize: 31, height: 1.15, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 10),
                  Text('Đăng nhập để xem và quản lý lịch uống thuốc của người thân.', style: TextStyle(color: colors.onSurfaceVariant, height: 1.5)),
                  const SizedBox(height: 28),
                  TextField(controller: _email, keyboardType: TextInputType.emailAddress, textInputAction: TextInputAction.next, decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline))),
                  const SizedBox(height: 14),
                  TextField(controller: _password, obscureText: true, onSubmitted: (_) => _busy ? null : _submit(), decoration: const InputDecoration(labelText: 'Mật khẩu', prefixIcon: Icon(Icons.lock_outline))),
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Text(_error!, style: TextStyle(color: colors.error), textAlign: TextAlign.center),
                  ],
                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: _busy ? null : _submit,
                    icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.arrow_forward),
                    label: Text(_busy ? 'Đang đăng nhập…' : 'Đăng nhập'),
                  ),
                  const SizedBox(height: 18),
                  Text('Dữ liệu demo · Token chỉ lưu trong phiên mở ứng dụng', textAlign: TextAlign.center, style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
