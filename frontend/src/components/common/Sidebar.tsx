import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  FolderOpen,
  BarChart3,
  Settings,
  Plus
} from 'lucide-react';
import { useRegistrationStore } from '../../stores/useRegistrationStore';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  children?: NavItem[];
}

const navItems: NavItem[] = [
  {
    to: '/dashboard',
    icon: <LayoutDashboard size={20} />,
    label: '대시보드',
  },
  {
    to: '/customers',
    icon: <Users size={20} />,
    label: '고객 관리',
  },
  {
    to: '/contracts',
    icon: <FileText size={20} />,
    label: '계약 관리',
  },
  {
    to: '/report',
    icon: <BarChart3 size={20} />,
    label: '리포트',
  },
  {
    to: '/settings',
    icon: <Settings size={20} />,
    label: '설정',
  },
];

const Sidebar: React.FC = () => {
  const { openModal, startNewSession } = useRegistrationStore();

  const handleNewRegistration = () => {
    startNewSession();
    openModal();
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-blue-600">KT 가입 시스템</h1>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <NavItem key={item.to} item={item} />
          ))}
        </ul>
      </nav>
      
      {/* New Registration Button */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={handleNewRegistration}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg hover:shadow-xl"
        >
          <Plus size={20} />
          신규 등록
        </button>
      </div>
    </div>
  );
};

const NavItem: React.FC<{ item: NavItem; isChild?: boolean }> = ({ item, isChild = false }) => {
  const [isOpen, setIsOpen] = React.useState(true);

  return (
    <li>
      <NavLink
        to={item.to}
        className={({ isActive }) =>
          `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
            isChild ? 'pl-10 text-sm' : ''
          } ${
            isActive
              ? 'bg-blue-50 text-blue-600 font-medium'
              : 'text-gray-700 hover:bg-gray-50'
          }`
        }
        onClick={(e) => {
          if (item.children && item.children.length > 0) {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
      >
        {item.icon}
        <span className="flex-1">{item.label}</span>
        {item.children && item.children.length > 0 && (
          <span className="text-gray-400">
            {isOpen ? '▼' : '▶'}
          </span>
        )}
      </NavLink>
      
      {item.children && item.children.length > 0 && isOpen && (
        <ul className="mt-1 space-y-1">
          {item.children.map((child) => (
            <NavItem key={child.to} item={child} isChild />
          ))}
        </ul>
      )}
    </li>
  );
};

export default Sidebar;

