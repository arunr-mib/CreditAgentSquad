export interface DemoUser {
  email: string;
  name: string;
  title: string;
  role: string;
}

/** The demonstration users (backend/app/seed_users.py). Listed so a reviewer can try each role as the person who holds it. */
export const DEMO_USERS: DemoUser[] = [
  { email: 'priya.raman@bankofstoic.example', name: 'Priya Raman', title: 'Senior Credit Analyst', role: 'analyst' },
  { email: 'tomas.keller@bankofstoic.example', name: 'Tomas Keller', title: 'Credit Analyst', role: 'analyst' },
  { email: 'dana.whitfield@bankofstoic.example', name: 'Dana Whitfield', title: 'Portfolio Manager', role: 'portfolio_manager' },
  { email: 'helen.strand@bankofstoic.example', name: 'Helen Strand', title: 'Senior Credit Officer', role: 'credit_officer' },
  { email: 'li.zhang@bankofstoic.example', name: 'Li Zhang', title: 'Credit Administration Lead', role: 'credit_admin' },
  { email: 'ruth.calloway@bankofstoic.example', name: 'Ruth Calloway', title: 'Credit Review Officer', role: 'credit_review' },
  { email: 'admin@bankofstoic.example', name: 'Platform Administrator', title: 'Administrator', role: 'admin' },
];

export const DEMO_PASSWORD = 'squad-demo';

/** Build with VITE_DEMO_USERS=off for a deployment with real accounts: the list is then not in the page at all. */
export const SHOW_DEMO_USERS = import.meta.env.VITE_DEMO_USERS !== 'off';
