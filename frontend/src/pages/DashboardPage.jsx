          {/* Performance Metrics Cards */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-gray-400 text-sm flex items-center space-x-1">
                <Cpu className="w-4 h-4" />
                <span>{t('cpu_usage')}</span>
              </div>
              <div className="text-white font-semibold">
                {dashboardData?.metrics?.cpu || 0}%
              </div>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full rounded-full",
                  (dashboardData?.metrics?.cpu || 0) < 70 ? "bg-green-500" :
                  (dashboardData?.metrics?.cpu || 0) < 90 ? "bg-yellow-500" : "bg-red-500"
                )}
                style={{ width: `${dashboardData?.metrics?.cpu || 0}%` }}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-gray-400 text-sm flex items-center space-x-1">
                <Database className="w-4 h-4" />
                <span>{t('memory_usage')}</span>
              </div>
              <div className="text-white font-semibold">
                {dashboardData?.metrics?.memory || 0}%
              </div>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full rounded-full",
                  (dashboardData?.metrics?.memory || 0) < 70 ? "bg-green-500" :
                  (dashboardData?.metrics?.memory || 0) < 90 ? "bg-yellow-500" : "bg-red-500"
                )}
                style={{ width: `${dashboardData?.metrics?.memory || 0}%` }}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-gray-400 text-sm flex items-center space-x-1">
                <Upload className="w-4 h-4" />
                <span>{t('network_in')}</span>
              </div>
              <div className="text-white font-semibold">
                {formatNumber(dashboardData?.metrics?.networkIn || 0)}/s
              </div>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full bg-blue-500"
                style={{ 
                  width: `${Math.min(
                    ((dashboardData?.metrics?.networkIn || 0) / 
                    (dashboardData?.metrics?.networkInMax || 100)) * 100, 
                    100
                  )}%` 
                }}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-gray-400 text-sm flex items-center space-x-1">
                <Download className="w-4 h-4" />
                <span>{t('network_out')}</span>
              </div>
              <div className="text-white font-semibold">
                {formatNumber(dashboardData?.metrics?.networkOut || 0)}/s
              </div>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full bg-purple-500"
                style={{ 
                  width: `${Math.min(
                    ((dashboardData?.metrics?.networkOut || 0) / 
                    (dashboardData?.metrics?.networkOutMax || 100)) * 100, 
                    100
                  )}%` 
                }}
              />
            </div>
          </div>
        </div>
        
        {/* Additional Performance Info */}
        {dashboardData?.metrics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-700">
            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
              <div className="text-gray-400 text-sm">{t('response_time')}</div>
              <div className="text-white font-semibold">
                {dashboardData.metrics.responseTime || 0}ms
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
              <div className="text-gray-400 text-sm">{t('error_rate')}</div>
              <div className={cn(
                "font-semibold",
                (dashboardData.metrics.errorRate || 0) < 0.01 ? "text-green-500" :
                (dashboardData.metrics.errorRate || 0) < 0.05 ? "text-yellow-500" : "text-red-500"
              )}>
                {((dashboardData.metrics.errorRate || 0) * 100).toFixed(2)}%
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
              <div className="text-gray-400 text-sm">{t('uptime')}</div>
              <div className="text-white font-semibold">
                {((dashboardData.metrics.uptime || 0) * 100).toFixed(2)}%
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}