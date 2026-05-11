class UserModel {
  const UserModel({required this.name, required this.email});

  final String name;
  final String email;

  Map<String, dynamic> toMap() {
    return {'name': name, 'email': email};
  }

  factory UserModel.fromMap(Map<String, dynamic> map) {
    return UserModel(
      name: map['name'] as String? ?? '',
      email: map['email'] as String? ?? '',
    );
  }
}
