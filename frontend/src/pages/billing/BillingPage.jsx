/**
 * Billing and Credits Management Page
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  CreditCard,
  DollarSign,
  FileText,
  History,
  TrendingUp,
  Zap,
  Check,
  AlertCircle,
  Download,
  RefreshCw,
  Calendar,
  PieChart,
  Bell,
  Shield
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { BillingService } from '../../services/api/billingService';
import { formatCurrency, formatDate } from '../../utils/formatters';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { ErrorDisplay } from '../../components/ErrorDisplay';
import { CreditPurchaseModal } from '../../components/modals/CreditPurchaseModal';
import { InvoiceModal } from '../../components/modals/InvoiceModal';
import { PaymentModal } from '../../components/modals/PaymentModal';

export default function BillingPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  
  // Fetch billing data
  const { data: balanceData, isLoading: balanceLoading, error: balanceError } = useQuery({
    queryKey: ['billing', 'balance'],
    queryFn: () => BillingService.getBalance(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
  
  const { data: invoicesData, isLoading: invoicesLoading } = useQuery({
    queryKey: ['billing', 'invoices'],
    queryFn: () => BillingService.getInvoices(),
    enabled: activeTab === 'invoices'
  });
  
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['billing', 'history'],
    queryFn: () => BillingService.getHistory({ limit: 50 }),
    enabled: activeTab === 'history'
  });
  
  const { data: estimateData, isLoading: estimateLoading } = useQuery({
    queryKey: ['billing', 'estimate'],
    queryFn: () => BillingService.getCostEstimate(),
    enabled: activeTab === 'analytics'
  });
  
  const { data: pricingData, isLoading: pricingLoading } = useQuery({
    queryKey: ['billing', 'pricing'],
    queryFn: () => BillingService.getPricing(),
  });
  
  // Generate invoice mutation
  const generateInvoiceMutation = useMutation({
    mutationFn: () => BillingService.generateInvoice(),
    onSuccess: () => {
      toast.success(t('invoice_generated_success'));
      queryClient.invalidateQueries(['billing', 'invoices']);
      queryClient.invalidateQueries(['billing', 'balance']);
    },
    onError: (error) => {
      toast.error(error.message || t('invoice_generation_failed'));
    }
  });
  
  // Handle invoice selection
  const handleViewInvoice = (invoice) => {
    setSelectedInvoice(invoice);
    setShowInvoiceModal(true);
  };
  
  // Handle payment
  const handlePayInvoice = (invoice) => {
    setSelectedInvoice(invoice);
    setShowPaymentModal(true);
  };
  
  // Download invoice
  const handleDownloadInvoice = async (invoice) => {
    try {
      const response = await BillingService.downloadInvoice(invoice.invoice_id);
      const blob = new Blob([response], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoice.invoice_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      toast.error(t('download_failed'));
    }
  };
  
  // Tabs configuration
  const tabs = [
    { id: 'overview', label: t('overview'), icon: PieChart },
    { id: 'credits', label: t('credits'), icon: Zap },
    { id: 'invoices', label: t('invoices'), icon: FileText },
    { id: 'history', label: t('history'), icon: History },
    { id: 'analytics', label: t('analytics'), icon: TrendingUp },
  ];
  
  if (balanceLoading && activeTab === 'overview') {
    return <LoadingSpinner message={t('loading_billing_info')} />;
  }
  
  if (balanceError) {
    return <ErrorDisplay error={balanceError} />;
  }
  
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              {t('billing_credits')}
            </h1>
            <p className="text-gray-400 mt-2">
              {t('manage_your_billing_and_credits')}
            </p>
          </div>
          
          {/* Quick Actions */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowPurchaseModal(true)}
              className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center space-x-2"
            >
              <CreditCard className="w-5 h-5" />
              <span>{t('buy_credits')}</span>
            </button>
            
            <button
              onClick={() => generateInvoiceMutation.mutate()}
              disabled={generateInvoiceMutation.isLoading}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center space-x-2 disabled:opacity-50"
            >
              {generateInvoiceMutation.isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <FileText className="w-5 h-5" />
              )}
              <span>{t('generate_invoice')}</span>
            </button>
          </div>
        </div>
      </div>
      
      {/* Credit Balance Card */}
      <div className="mb-8">
        <div className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-2xl p-8 border border-gray-700">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {balanceData?.available_credits?.toLocaleString() || 0} {t('credits')}
                  </h2>
                  <p className="text-gray-400">
                    {t('available_balance')}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">{t('total_credits')}</div>
                  <div className="text-xl font-bold text-white">
                    {balanceData?.total_credits?.toLocaleString() || 0}
                  </div>
                </div>
                
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">{t('used_credits')}</div>
                  <div className="text-xl font-bold text-white">
                    {balanceData?.used_credits?.toLocaleString() || 0}
                  </div>
                </div>
                
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">{t('deferred_balance')}</div>
                  <div className="text-xl font-bold text-white">
                    {formatCurrency(balanceData?.deferred_balance || 0, balanceData?.currency)}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="lg:w-1/3">
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-gray-400">{t('credit_usage')}</span>
                <span className="text-white">
                  {Math.round(((balanceData?.used_credits || 0) / (balanceData?.total_credits || 1)) * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div 
                  className="bg-gradient-to-r from-green-400 to-blue-400 h-3 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${Math.min(((balanceData?.used_credits || 0) / (balanceData?.total_credits || 1)) * 100, 100)}%` 
                  }}
                />
              </div>
              
              {/* Trial Status */}
              {balanceData?.is_trial_active && (
                <div className="mt-6 p-4 bg-gradient-to-r from-yellow-900 to-amber-900 rounded-lg border border-yellow-700">
                  <div className="flex items-center space-x-2 mb-2">
                    <Bell className="w-5 h-5 text-yellow-400" />
                    <div className="font-medium text-yellow-300">{t('free_trial_active')}</div>
                  </div>
                  <div className="text-sm text-yellow-200">
                    {t('trial_ends_on')} {formatDate(balanceData.trial_end_date)}
                  </div>
                  <div className="text-xs text-yellow-300 mt-2">
                    {t('trial_credits_remaining', { credits: balanceData.available_credits })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-8">
        <div className="border-b border-gray-700">
          <nav className="flex space-x-8 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap",
                  activeTab === tab.id
                    ? "border-purple-500 text-purple-400"
                    : "border-transparent text-gray-400 hover:text-gray-300"
                )}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>
      
      {/* Tab Content */}
      <div className="mt-8">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Current Period Usage */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-medium text-gray-300 mb-4 flex items-center space-x-2">
                <Calendar className="w-5 h-5" />
                <span>{t('current_period_usage')}</span>
              </h3>
              
              {balanceData?.current_period_usage ? (
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">{t('period')}</span>
                      <span className="text-white">
                        {formatDate(balanceData.current_period_usage.period_start)} - {formatDate(balanceData.current_period_usage.period_end)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">{t('total_cost')}</span>
                      <span className="text-white font-medium">
                        {formatCurrency(balanceData.current_period_usage.total_cost, balanceData.currency)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">{t('credits_used')}</span>
                      <span className="text-white">
                        {balanceData.current_period_usage.total_credits.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  
                  {/* Usage by Service */}
                  <div className="mt-6">
                    <h4 className="text-sm font-medium text-gray-400 mb-3">{t('usage_by_service')}</h4>
                    <div className="space-y-3">
                      {Object.entries(balanceData.current_period_usage.by_service || {}).map(([service, data]) => (
                        <div key={service} className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                            <span className="text-sm text-gray-300 capitalize">{service.replace('_', ' ')}</span>
                          </div>
                          <div className="text-sm text-white">
                            {formatCurrency(data.cost, balanceData.currency)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  {t('no_usage_data')}
                </div>
              )}
            </div>
            
            {/* Pricing Information */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-medium text-gray-300 mb-4 flex items-center space-x-2">
                <DollarSign className="w-5 h-5" />
                <span>{t('pricing_info')}</span>
              </h3>
              
              {pricingLoading ? (
                <LoadingSpinner />
              ) : pricingData ? (
                <div className="space-y-4">
                  <div className="bg-gray-900 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm text-gray-400">{t('credit_price')}</div>
                      <div className="text-lg font-bold text-white">
                        {formatCurrency(pricingData.credit_price, pricingData.currency)}
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">
                      {t('per_credit')}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-3">{t('service_costs')}</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-300">{t('voice_processing')}</span>
                        <span className="text-white">
                          {pricingData.services?.voice_processing?.per_minute || 0} {t('credits_per_min')}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-300">{t('chat_messages')}</span>
                        <span className="text-white">
                          {pricingData.services?.chat_processing?.per_message || 0} {t('credits_per_msg')}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-300">{t('face_processing')}</span>
                        <span className="text-white">
                          {pricingData.services?.face_processing?.per_image || 0} {t('credits_per_image')}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Deferred Payment Info */}
                  <div className="mt-6 pt-6 border-t border-gray-700">
                    <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center space-x-2">
                      <Shield className="w-4 h-4" />
                      <span>{t('deferred_payment')}</span>
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-300">{t('grace_period')}</span>
                        <span className="text-white">
                          {pricingData.deferred_payment?.grace_days || 0} {t('days')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">{t('minimum_amount')}</span>
                        <span className="text-white">
                          {formatCurrency(pricingData.deferred_payment?.min_amount || 0, pricingData.currency)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  {t('no_pricing_data')}
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Credits Tab */}
        {activeTab === 'credits' && (
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-8">
              <div>
                <h3 className="text-xl font-medium text-gray-300 mb-2">
                  {t('manage_credits')}
                </h3>
                <p className="text-gray-400">
                  {t('credits_management_description')}
                </p>
              </div>
              
              <button
                onClick={() => setShowPurchaseModal(true)}
                className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center space-x-2"
              >
                <CreditCard className="w-5 h-5" />
                <span>{t('buy_credits')}</span>
              </button>
            </div>
            
            {/* Credit Packages */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { credits: 1000, price: 10, popular: false },
                { credits: 5000, price: 45, popular: true, discount: 10 },
                { credits: 10000, price: 80, popular: false, discount: 20 },
              ].map((packageInfo) => (
                <div 
                  key={packageInfo.credits}
                  className={cn(
                    "bg-gray-900 rounded-xl p-6 border-2 transition-all hover:scale-[1.02]",
                    packageInfo.popular 
                      ? "border-purple-500 relative" 
                      : "border-gray-700"
                  )}
                >
                  {packageInfo.popular && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-1 rounded-full text-xs font-medium">
                        {t('most_popular')}
                      </div>
                    </div>
                  )}
                  
                  <div className="text-center mb-6">
                    <div className="text-3xl font-bold text-white mb-2">
                      {packageInfo.credits.toLocaleString()}
                    </div>
                    <div className="text-gray-400">{t('credits')}</div>
                  </div>
                  
                  <div className="text-center mb-6">
                    <div className="text-2xl font-bold text-white mb-1">
                      {formatCurrency(packageInfo.price, balanceData?.currency || 'USD')}
                    </div>
                    {packageInfo.discount && (
                      <div className="text-sm text-green-400">
                        {t('save_percentage', { percent: packageInfo.discount })}
                      </div>
                    )}
                    <div className="text-xs text-gray-500 mt-1">
                      {t('credit_value', { 
                        value: formatCurrency(packageInfo.price / packageInfo.credits, balanceData?.currency || 'USD')
                      })}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => setShowPurchaseModal(true)}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:opacity-90 transition-opacity"
                  >
                    {t('select_package')}
                  </button>
                </div>
              ))}
            </div>
            
            {/* Credit Usage Tips */}
            <div className="mt-8 pt-8 border-t border-gray-700">
              <h4 className="text-lg font-medium text-gray-300 mb-4">{t('credit_usage_tips')}</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-start space-x-3 p-4 bg-gray-900 rounded-lg">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-300 mb-1">{t('tip_efficient_chat')}</div>
                    <div className="text-sm text-gray-400">{t('tip_efficient_chat_desc')}</div>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 p-4 bg-gray-900 rounded-lg">
                  <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-300 mb-1">{t('tip_bulk_processing')}</div>
                    <div className="text-sm text-gray-400">{t('tip_bulk_processing_desc')}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Invoices Tab */}
        {activeTab === 'invoices' && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="p-6 border-b border-gray-700">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-xl font-medium text-gray-300 mb-2">
                    {t('invoices')}
                  </h3>
                  <p className="text-gray-400">
                    {t('invoices_description')}
                  </p>
                </div>
                
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => generateInvoiceMutation.mutate()}
                    disabled={generateInvoiceMutation.isLoading}
                    className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center space-x-2 disabled:opacity-50"
                  >
                    {generateInvoiceMutation.isLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                    <span>{t('generate_invoice')}</span>
                  </button>
                </div>
              </div>
            </div>
            
            {invoicesLoading ? (
              <div className="p-12 text-center">
                <LoadingSpinner />
              </div>
            ) : invoicesData?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('invoice_number')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('period')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('amount')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('due_date')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('status')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('actions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {invoicesData.map((invoice) => (
                      <tr key={invoice.invoice_id} className="hover:bg-gray-750">
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="text-sm font-medium text-white">
                            {invoice.invoice_number}
                          </div>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="text-sm text-gray-300">
                            {formatDate(invoice.period.split(' to ')[0])}
                          </div>
                          <div className="text-xs text-gray-500">
                            {t('to')} {formatDate(invoice.period.split(' to ')[1])}
                          </div>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="text-sm font-medium text-white">
                            {formatCurrency(invoice.amount, invoice.currency)}
                          </div>
                          {invoice.late_fee > 0 && (
                            <div className="text-xs text-red-400">
                              +{formatCurrency(invoice.late_fee, invoice.currency)} {t('late_fee')}
                            </div>
                          )}
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className={cn(
                            "text-sm",
                            invoice.status === 'overdue' ? 'text-red-400' : 'text-gray-300'
                          )}>
                            {formatDate(invoice.due_date)}
                          </div>
                          {invoice.days_overdue > 0 && (
                            <div className="text-xs text-red-400">
                              {invoice.days_overdue} {t('days_overdue')}
                            </div>
                          )}
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <span className={cn(
                            "px-3 py-1 rounded-full text-xs font-medium",
                            invoice.status === 'paid' 
                              ? "bg-green-500 bg-opacity-20 text-green-400"
                              : invoice.status === 'overdue'
                              ? "bg-red-500 bg-opacity-20 text-red-400"
                              : "bg-yellow-500 bg-opacity-20 text-yellow-400"
                          )}>
                            {t(invoice.status)}
                          </span>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleViewInvoice(invoice)}
                              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                              title={t('view_invoice')}
                            >
                              <FileText className="w-4 h-4" />
                            </button>
                            
                            {invoice.status !== 'paid' && (
                              <button
                                onClick={() => handlePayInvoice(invoice)}
                                className="p-2 text-green-400 hover:text-green-300 hover:bg-gray-700 rounded-lg transition-colors"
                                title={t('pay_invoice')}
                              >
                                <CreditCard className="w-4 h-4" />
                              </button>
                            )}
                            
                            <button
                              onClick={() => handleDownloadInvoice(invoice)}
                              className="p-2 text-blue-400 hover:text-blue-300 hover:bg-gray-700 rounded-lg transition-colors"
                              title={t('download_invoice')}
                            >
                              <Download className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <div className="text-gray-500 text-lg mb-2">{t('no_invoices')}</div>
                <p className="text-gray-600 mb-6">{t('no_invoices_description')}</p>
                <button
                  onClick={() => generateInvoiceMutation.mutate()}
                  disabled={generateInvoiceMutation.isLoading}
                  className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {generateInvoiceMutation.isLoading ? t('generating') : t('generate_first_invoice')}
                </button>
              </div>
            )}
          </div>
        )}
        
        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-medium text-gray-300 mb-2">
                {t('billing_history')}
              </h3>
              <p className="text-gray-400">
                {t('billing_history_description')}
              </p>
            </div>
            
            {historyLoading ? (
              <div className="p-12 text-center">
                <LoadingSpinner />
              </div>
            ) : historyData?.transactions?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900">
                    <tr>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('date')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('description')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('type')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('credits')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('amount')}
                      </th>
                      <th className="py-3 px-6 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        {t('status')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {historyData.transactions.map((transaction) => (
                      <tr key={transaction.id} className="hover:bg-gray-750">
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="text-sm text-gray-300">
                            {formatDate(transaction.created_at, 'short')}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <div className="text-sm text-white">
                            {transaction.description}
                          </div>
                          {transaction.service_type && (
                            <div className="text-xs text-gray-500 capitalize">
                              {transaction.service_type.replace('_', ' ')}
                            </div>
                          )}
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <span className={cn(
                            "px-3 py-1 rounded-full text-xs font-medium",
                            transaction.amount > 0
                              ? "bg-green-500 bg-opacity-20 text-green-400"
                              : "bg-red-500 bg-opacity-20 text-red-400"
                          )}>
                            {t(transaction.type)}
                          </span>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="text-sm text-white">
                            {transaction.credits_granted 
                              ? `+${transaction.credits_granted.toLocaleString()}`
                              : transaction.credits_used 
                                ? `-${transaction.credits_used.toLocaleString()}`
                                : '0'
                            }
                          </div>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className={cn(
                            "text-sm font-medium",
                            transaction.amount > 0 ? "text-green-400" : "text-red-400"
                          )}>
                            {formatCurrency(Math.abs(transaction.amount), balanceData?.currency || 'USD')}
                          </div>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <span className={cn(
                            "px-3 py-1 rounded-full text-xs font-medium",
                            transaction.status === 'completed'
                              ? "bg-green-500 bg-opacity-20 text-green-400"
                              : transaction.status === 'failed'
                              ? "bg-red-500 bg-opacity-20 text-red-400"
                              : "bg-yellow-500 bg-opacity-20 text-yellow-400"
                          )}>
                            {t(transaction.status)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {/* Pagination */}
                {historyData.total_transactions > historyData.limit && (
                  <div className="p-6 border-t border-gray-700">
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-gray-400">
                        {t('showing_transactions', {
                          from: historyData.offset + 1,
                          to: Math.min(historyData.offset + historyData.limit, historyData.total_transactions),
                          total: historyData.total_transactions
                        })}
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          disabled={historyData.offset === 0}
                          className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
                        >
                          {t('previous')}
                        </button>
                        <button
                          disabled={historyData.offset + historyData.limit >= historyData.total_transactions}
                          className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
                        >
                          {t('next')}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center">
                <History className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <div className="text-gray-500 text-lg mb-2">{t('no_transactions')}</div>
                <p className="text-gray-600">{t('no_transactions_description')}</p>
              </div>
            )}
          </div>
        )}
        
        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {estimateLoading ? (
              <div className="col-span-2">
                <LoadingSpinner />
              </div>
            ) : estimateData ? (
              <>
                {/* Cost Estimate */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                  <h3 className="text-lg font-medium text-gray-300 mb-6 flex items-center space-x-2">
                    <TrendingUp className="w-5 h-5" />
                    <span>{t('monthly_cost_estimate')}</span>
                  </h3>
                  
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-900 rounded-lg p-4">
                        <div className="text-sm text-gray-400 mb-1">{t('daily_average')}</div>
                        <div className="text-2xl font-bold text-white">
                          {formatCurrency(estimateData.daily_average, estimateData.currency)}
                        </div>
                      </div>
                      
                      <div className="bg-gray-900 rounded-lg p-4">
                        <div className="text-sm text-gray-400 mb-1">{t('monthly_estimate')}</div>
                        <div className="text-2xl font-bold text-white">
                          {formatCurrency(estimateData.monthly_estimate, estimateData.currency)}
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-400">{t('based_on_period')}</span>
                        <span className="text-white">{estimateData.period_days} {t('days')}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">{t('actual_cost')}</span>
                        <span className="text-white">
                          {formatCurrency(estimateData.actual_cost, estimateData.currency)}
                        </span>
                      </div>
                    </div>
                    
                    {/* Cost Breakdown */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-3">{t('cost_breakdown')}</h4>
                      <div className="space-y-3">
                        {Object.entries(estimateData.breakdown || {}).map(([service, cost]) => (
                          <div key={service} className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                              <span className="text-sm text-gray-300 capitalize">{service.replace('_', ' ')}</span>
                            </div>
                            <div className="text-sm text-white">
                              {formatCurrency(cost, estimateData.currency)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Usage Recommendations */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                  <h3 className="text-lg font-medium text-gray-300 mb-6 flex items-center space-x-2">
                    <AlertCircle className="w-5 h-5" />
                    <span>{t('usage_recommendations')}</span>
                  </h3>
                  
                  <div className="space-y-4">
                    {estimateData.monthly_estimate > 50 && (
                      <div className="p-4 bg-gradient-to-r from-yellow-900 to-amber-900 rounded-lg border border-yellow-700">
                        <div className="flex items-start space-x-3">
                          <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="font-medium text-yellow-300 mb-1">{t('high_usage_alert')}</div>
                            <div className="text-sm text-yellow-200">
                              {t('consider_bulk_credit_purchase')}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div className="p-4 bg-gray-900 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="font-medium text-gray-300 mb-1">{t('optimize_chat_usage')}</div>
                          <div className="text-sm text-gray-400">
                            {t('chat_usage_tips')}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="p-4 bg-gray-900 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="font-medium text-gray-300 mb-1">{t('schedule_tasks_wisely')}</div>
                          <div className="text-sm text-gray-400">
                            {t('task_scheduling_tips')}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="p-4 bg-gray-900 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="font-medium text-gray-300 mb-1">{t('manage_storage')}</div>
                          <div className="text-sm text-gray-400">
                            {t('storage_management_tips')}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="col-span-2 text-center py-12">
                <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <div className="text-gray-500 text-lg mb-2">{t('no_analytics_data')}</div>
                <p className="text-gray-600">{t('analytics_data_will_appear')}</p>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Modals */}
      {showPurchaseModal && (
        <CreditPurchaseModal
          isOpen={showPurchaseModal}
          onClose={() => setShowPurchaseModal(false)}
          currency={balanceData?.currency}
          creditPrice={pricingData?.credit_price}
          onSuccess={() => {
            queryClient.invalidateQueries(['billing', 'balance']);
            queryClient.invalidateQueries(['billing', 'history']);
          }}
        />
      )}
      
      {showInvoiceModal && selectedInvoice && (
        <InvoiceModal
          isOpen={showInvoiceModal}
          onClose={() => {
            setShowInvoiceModal(false);
            setSelectedInvoice(null);
          }}
          invoice={selectedInvoice}
          onPay={() => {
            setShowInvoiceModal(false);
            setShowPaymentModal(true);
          }}
          onDownload={handleDownloadInvoice}
        />
      )}
      
      {showPaymentModal && selectedInvoice && (
        <PaymentModal
          isOpen={showPaymentModal}
          onClose={() => {
            setShowPaymentModal(false);
            setSelectedInvoice(null);
          }}
          invoice={selectedInvoice}
          onSuccess={() => {
            queryClient.invalidateQueries(['billing', 'invoices']);
            queryClient.invalidateQueries(['billing', 'balance']);
            queryClient.invalidateQueries(['billing', 'history']);
          }}
        />
      )}
    </div>
  );
}