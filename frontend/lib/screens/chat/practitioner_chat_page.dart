import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../widgets/persona_chat_scaffold.dart';

class PractitionerChatPage extends StatelessWidget {
  const PractitionerChatPage({super.key});

  static const _accent = Color(0xFF1E6F9F);

  @override
  Widget build(BuildContext context) {
    return PersonaChatScaffold(
      personaLabel: "Practitioner",
      userTypeKey: "practitioner",
      accentColor: _accent,
      icon: Icons.medical_services_outlined,
      greeting: "Ask about medicinal plants\nClinical detail, dosage notes, and contraindications included.",
      infoBanner: Container(
        width: double.infinity,
        color: _accent.withValues(alpha: 0.08),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.warning_amber_rounded, size: 16, color: Colors.orange[800]),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                "For clinical reference only — always verify against current pharmacological sources before advising patients.",
                style: TextStyle(fontSize: 12, color: AppColors.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}