const firstNames = [
  "Liam", "Olivia", "Noah", "Emma", "Oliver", "Ava", "Elijah", "Sophia", "James", "Isabella",
  "William", "Mia", "Benjamin", "Charlotte", "Lucas", "Amelia", "Henry", "Harper", "Alexander", "Evelyn",
  "Mason", "Abigail", "Michael", "Emily", "Ethan", "Elizabeth", "Daniel", "Avery", "Jacob", "Sofia",
  "Logan", "Ella", "Jackson", "Madison", "Levi", "Scarlett", "Sebastian", "Victoria", "Mateo", "Aria",
  "Jack", "Grace", "Owen", "Chloe", "Theodore", "Camila", "Aiden", "Penelope", "Samuel", "Riley",
  "Joseph", "Layla", "John", "Lillian", "David", "Nora", "Wyatt", "Zoey", "Matthew", "Mila",
  "Luke", "Aubrey", "Asher", "Hannah", "Carter", "Lily", "Julian", "Addison", "Grayson", "Eleanor",
  "Leo", "Natalie", "Jayden", "Luna", "Gabriel", "Savannah", "Isaac", "Brooklyn", "Lincoln", "Leah",
  "Anthony", "Zoe", "Hudson", "Stella", "Dylan", "Hazel", "Ezra", "Ellie", "Thomas", "Paisley",
  "Charles", "Audrey", "Christopher", "Skylar", "Jaxon", "Violet", "Maverick", "Claire", "Josiah", "Bella"
];

const lastNames = [
  "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
  "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
  "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
  "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
  "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
  "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
  "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
  "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
  "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez"
];

function randomCgpa() {
  const value = 2 + Math.random() * 2; // 2.00 - 4.00
  return Math.round(value * 100) / 100;
}

function generateStudents() {
  const students = [];
  for (let i = 0; i < 100; i++) {
    const firstName = firstNames[i];
    const lastName = lastNames[i];
    students.push({
      studentId: 3005001 + i,
      firstName,
      lastName,
      password: lastName + "123",
      cgpa: randomCgpa()
    });
  }
  return students;
}

module.exports = { firstNames, lastNames, generateStudents };
