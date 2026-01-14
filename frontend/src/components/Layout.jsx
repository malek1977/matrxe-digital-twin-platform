/**
 * Main Layout Component
 */

import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { 
  Home, 
  Users, 
  MessageSquare, 
  Calendar, 
  CreditCard,
  Settings,
  User,
  LogOut,
  Menu,
  X,
  Globe,
  Moon,
  Sun,
  Bell,
  Search,
  ChevronDown,
  Zap
} from 'lucide-react';
import { cn } from '../utils/cn';
import { LanguageSwitcher } from './LanguageSwitcher';
import { NotificationsPanel } from './NotificationsPanel';
import { UserMenu } from './UserMenu';

export function Layout() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [credits, setCredits] = useState(user?.credits || 1000);

  // Navigation items
  const navItems = [
    { path: '/app/dashboard', icon: Home, label: t('nav_dashboard'), exact: true },
    { path: '/app/twins', icon: Users, label: t('nav_my_twins') },
    { path: '/app/chat', icon: MessageSquare, label: t('nav_conversations') },
    { path: '/app/tasks', icon: Calendar, label: t('nav_scheduled_tasks') },
    { path: '/app/billing', icon: CreditCard, label: t('nav_billing') },
    { path: '/app/settings', icon: Settings, label: t('nav_settings') },
  ];

  // Handle logout
  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Handle search
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Implement search functionality
      console.log('Search:', searchQuery);
    }
  };

  // Close sidebar on mobile when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (sidebarOpen && !e.target.closest('.sidebar') && !e.target.closest('.menu-button')) {
        setSidebarOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [sidebarOpen]);

  // Simulate credits update (replace with real API call)
  useEffect(() => {
    if (user) {
      // Fetch actual credits from API
      setCredits(user.credits || 1000);
    }
  }, [user]);

  if (!isAuthenticated) {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "sidebar fixed inset-y-0 left-0 z-50 w-64 bg-gray-800 border-r border-gray-700 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-auto",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-gray-700">
            <Link to="/app/dashboard" className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center">
                <Zap className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                  MATRXe
                </h1>
                <p className="text-xs text-gray-400">Digital Twins</p>
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = item.exact 
                ? location.pathname === item.path
                : location.pathname.startsWith(item.path);
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    "flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200",
                    isActive
                      ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg"
                      : "text-gray-300 hover:bg-gray-700 hover:text-white"
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                  {isActive && (
                    <div className="ml-auto w-2 h-2 rounded-full bg-white" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Credits & Trial Status */}
          <div className="p-4 border-t border-gray-700">
            <div className="bg-gradient-to-r from-gray-700 to-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">{t('credits_remaining')}</span>
                <div className="flex items-center space-x-1">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  <span className="font-bold text-lg">{credits.toLocaleString()}</span>
                </div>
              </div>
              <div className="w-full bg-gray-600 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-green-400 to-blue-400 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min((credits / 1000) * 100, 100)}%` }}
                />
              </div>
              {user?.trial_end_date && (
                <div className="mt-3 text-xs text-gray-400">
                  {t('free_trial_active')}: {new Date(user.trial_end_date).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Top Navigation */}
        <header className="sticky top-0 z-30 bg-gray-800 bg-opacity-90 backdrop-blur-lg border-b border-gray-700">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Left: Menu button and search */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="menu-button lg:hidden p-2 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  {sidebarOpen ? (
                    <X className="w-6 h-6" />
                  ) : (
                    <Menu className="w-6 h-6" />
                  )}
                </button>

                {/* Search */}
                <form onSubmit={handleSearch} className="hidden md:block">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t('search_placeholder') || "Search..."}
                      className="pl-10 pr-4 py-2 w-64 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>
                </form>
              </div>

              {/* Right: User actions */}
              <div className="flex items-center space-x-4">
                {/* Language Switcher */}
                <LanguageSwitcher />

                {/* Theme Toggle */}
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
                  title={theme === 'dark' ? t('switch_to_light') : t('switch_to_dark')}
                >
                  {theme === 'dark' ? (
                    <Sun className="w-5 h-5" />
                  ) : (
                    <Moon className="w-5 h-5" />
                  )}
                </button>

                {/* Notifications */}
                <div className="relative">
                  <button
                    onClick={() => setNotificationsOpen(!notificationsOpen)}
                    className="p-2 rounded-lg hover:bg-gray-700 transition-colors relative"
                  >
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  </button>
                  {notificationsOpen && (
                    <NotificationsPanel onClose={() => setNotificationsOpen(false)} />
                  )}
                </div>

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                      <User className="w-5 h-5" />
                    </div>
                    <div className="hidden md:block text-left">
                      <div className="text-sm font-medium">
                        {user?.full_name || user?.username}
                      </div>
                      <div className="text-xs text-gray-400">
                        {user?.subscription_tier === 'trial' ? t('free_trial') : t('premium_user')}
                      </div>
                    </div>
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  </button>
                  {userMenuOpen && (
                    <UserMenu 
                      user={user} 
                      onClose={() => setUserMenuOpen(false)}
                      onLogout={handleLogout}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-700 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-gray-400 text-sm">
              © {new Date().getFullYear()} MATRXe. {t('all_rights_reserved')}.
            </div>
            <div className="flex items-center space-x-6">
              <Link to="/privacy" className="text-gray-400 hover:text-white text-sm transition-colors">
                {t('privacy_policy')}
              </Link>
              <Link to="/terms" className="text-gray-400 hover:text-white text-sm transition-colors">
                {t('terms_of_service')}
              </Link>
              <Link to="/help" className="text-gray-400 hover:text-white text-sm transition-colors">
                {t('help_center')}
              </Link>
              <a 
                href="mailto:support@matrxe.com" 
                className="text-gray-400 hover:text-white text-sm transition-colors"
              >
                {t('contact_support')}
              </a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}