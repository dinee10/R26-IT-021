import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

class PersonaMeta {
  final String key; // sent to / received from backend
  final String label;
  final String description;
  final IconData icon;
  final Color color;

  const PersonaMeta({
    required this.key,
    required this.label,
    required this.description,
    required this.icon,
    required this.color,
  });
}

final List<PersonaMeta> kPersonas = [
  PersonaMeta(
    key: "general_public",
    label: "General Public",
    description: "Simple, everyday explanations",
    icon: Icons.eco_outlined,
    color: AppColors.primary,
  ),
  const PersonaMeta(
    key: "practitioner",
    label: "Practitioner",
    description: "Clinical detail and safety notes",
    icon: Icons.medical_services_outlined,
    color: Color(0xFF1E6F9F),
  ),
  const PersonaMeta(
    key: "student",
    label: "Student",
    description: "Explanations for study and coursework",
    icon: Icons.school_outlined,
    color: Color(0xFF8B5CF6),
  ),
  const PersonaMeta(
    key: "researcher",
    label: "Researcher",
    description: "Evidence-forward, scientific detail",
    icon: Icons.science_outlined,
    color: Color(0xFF2E5E4E),
  ),
];

PersonaMeta personaByKey(String key) =>
    kPersonas.firstWhere((p) => p.key == key, orElse: () => kPersonas.first);

bool isKnownPersona(String key) => kPersonas.any((p) => p.key == key);

const int kMaxCategories = 2;

/// Adds/removes [key], keeping at most [kMaxCategories] (oldest dropped).
void togglePersona(List<String> selected, String key) {
  if (selected.contains(key)) {
    selected.remove(key);
  } else {
    if (selected.length >= kMaxCategories) selected.removeAt(0);
    selected.add(key);
  }
}