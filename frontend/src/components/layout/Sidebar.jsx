import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Building2,
  UserCog,
  CalendarDays,
  ClipboardList,
  Clock,
  MessageSquare,
  UserCheck,
  LogOut
} from 'lucide-react';
import NotificationBell from './NotificationBell';

const Sidebar = ({ user, onLogout }) => {
  const getNavItems = () => {
    if (user.user_type === 'admin') {
      return [
        { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/managers', icon: UserCog, label: 'Managers' },
        { path: '/departments', icon: Building2, label: 'Departments' },
      ];
    } else if (user.user_type === 'manager') {
      return [
        { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/employees', icon: Users, label: 'Employees' },
        { path: '/schedules', icon: CalendarDays, label: 'Schedules' },
        { path: '/roles', icon: ClipboardList, label: 'Role Management' },
        { path: '/leaves', icon: UserCheck, label: 'Leave Requests' },
        { path: '/attendance', icon: Clock, label: 'Attendance' },
        { path: '/messages', icon: MessageSquare, label: 'Messages' },
      ];
    } else {
      return [
        { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/check-in', icon: UserCheck, label: 'Check-In/Out' },
        { path: '/schedule', icon: CalendarDays, label: 'My Schedule' },
        { path: '/requests', icon: ClipboardList, label: 'Requests & Approvals' },
        { path: '/leaves', icon: UserCheck, label: 'Leave Requests' },
        { path: '/attendance', icon: Clock, label: 'My Attendance' },
        { path: '/messages', icon: MessageSquare, label: 'Messages' },
      ];
    }
  };

  const navItems = getNavItems();

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white w-64">
      {/* Logo */}
      <div className="p-6 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-bold">Shift Scheduler</h1>
          <NotificationBell />
        </div>
        <p className="text-sm text-gray-400 mt-1 capitalize">{user.user_type} Portal</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 mb-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Info & Logout */}
      <div className="p-4 border-t border-gray-700">
        <div className="px-4 py-2 mb-2">
          <p className="text-sm font-medium">{user.full_name}</p>
          <p className="text-xs text-gray-400">{user.email}</p>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center w-full px-4 py-3 text-gray-300 hover:bg-gray-800 hover:text-white rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5 mr-3" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
