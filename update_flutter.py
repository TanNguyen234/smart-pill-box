import os

def update_home_screen():
    with open('flutter-app/lib/screens/home_screen.dart', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add new params
    if 'final Future<List<Alert>> Function() onFetchAlerts;' not in content:
        content = content.replace(
            'final VoidCallback onLogout;',
            'final VoidCallback onLogout;\n  final Future<List<Alert>> Function() onFetchAlerts;\n  final Future<void> Function(int, String?) onResolveAlert;'
        )
        content = content.replace(
            'required this.onLogout,',
            'required this.onLogout,\n    required this.onFetchAlerts,\n    required this.onResolveAlert,'
        )

    # Add state variables
    if 'List<Alert> _alerts = [];' not in content:
        content = content.replace(
            'int _page = 0;',
            'int _page = 0;\n  List<Alert> _alerts = [];\n  bool _isLoadingAlerts = false;'
        )

    # Replace the _comingSoon for Cảnh báo with a new _alertsPage
    old_coming_soon_alerts = "_comingSoon(context, Icons.notifications_none, 'Cảnh báo', 'Cảnh báo sẽ được phát triển ở giai đoạn sau.')"
    # Wait, the source code had utf8 mojibake when viewed in console, but python reading with utf-8 should be fine.
    
    # We will search by index
    idx1 = content.find("_comingSoon(context, Icons.notifications_none, 'C")
    idx2 = content.find("),", idx1) + 2 if idx1 != -1 else -1
    
    if idx1 != -1 and idx2 != -1:
        content = content[:idx1] + "_alertsPage(context)" + content[idx2:]

    # Hook into navigation to load alerts
    content = content.replace(
        'onDestinationSelected: (index) => setState(() => _page = index),',
        '''onDestinationSelected: (index) {
          setState(() => _page = index);
          if (index == 3) _loadAlerts();
        },'''
    )

    # Add _loadAlerts and _alertsPage
    new_methods = '''
  Future<void> _loadAlerts() async {
    setState(() => _isLoadingAlerts = true);
    try {
      final alerts = await widget.onFetchAlerts();
      if (mounted) setState(() => _alerts = alerts);
    } finally {
      if (mounted) setState(() => _isLoadingAlerts = false);
    }
  }

  Future<void> _resolveAlert(Alert alert) async {
    final noteController = TextEditingController();
    final note = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Xử lý cảnh báo'),
        content: TextField(
          controller: noteController,
          decoration: const InputDecoration(hintText: 'Nhập ghi chú xử lý...'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Huỷ')),
          FilledButton(onPressed: () => Navigator.pop(c, noteController.text), child: const Text('Xác nhận')),
        ],
      ),
    );
    if (note != null) {
      await widget.onResolveAlert(alert.id, note.isEmpty ? null : note);
      await _loadAlerts();
    }
  }

  Widget _alertsPage(BuildContext context) => _isLoadingAlerts
      ? const Center(child: CircularProgressIndicator())
      : ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Danh sách cảnh báo', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
            if (_alerts.isEmpty) _emptyCard(context, 'Chưa có cảnh báo nào.') else ..._alerts.map((alert) {
              final isResolved = alert.resolvedAt != null;
              return Card(
                color: isResolved ? null : const Color(0xFFFFEBEB),
                child: ListTile(
                  leading: Icon(Icons.warning, color: isResolved ? Colors.grey : Colors.red),
                  title: Text(alert.message, style: TextStyle(color: isResolved ? Colors.grey : Colors.red.shade900, fontWeight: FontWeight.w600)),
                  subtitle: Text('Loại: ${alert.kind} - Lần nhắc: ${alert.occurrenceId}\\nThời gian: ${alert.createdAt}'),
                  trailing: isResolved
                      ? const Icon(Icons.check_circle, color: Colors.green)
                      : TextButton(onPressed: () => _resolveAlert(alert), child: const Text('XỬ LÝ')),
                  isThreeLine: true,
                ),
              );
            }),
          ],
        );
'''
    content += new_methods
    
    with open('flutter-app/lib/screens/home_screen.dart', 'w', encoding='utf-8') as f:
        f.write(content)

def update_main():
    with open('flutter-app/lib/main.dart', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'onFetchAlerts:' not in content:
        content = content.replace(
            'onLogout: _logout,',
            'onLogout: _logout,\n                onFetchAlerts: () => _api.getAlerts(),\n                onResolveAlert: (id, note) => _api.resolveAlert(id, note: note),'
        )
        
    with open('flutter-app/lib/main.dart', 'w', encoding='utf-8') as f:
        f.write(content)

update_home_screen()
update_main()
