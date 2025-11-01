// bot-status.js
// مراقبة حالة البوت في الوقت الفعلي

(function() {
    'use strict';
    
    // التحقق من حالة البوت كل 30 ثانية
    const CHECK_INTERVAL = 30000;
    let lastStatus = null;
    
    function checkBotStatus() {
        fetch('/bot-status', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // إذا تغيرت الحالة، أظهر تنبيه
            if (lastStatus !== null && lastStatus !== data.online) {
                showStatusAlert(data.online, data.message);
            }
            lastStatus = data.online;
            
            // تحديث مؤشر الحالة إذا كان موجوداً
            updateStatusIndicator(data.online);
        })
        .catch(error => {
            console.error('خطأ في التحقق من حالة البوت:', error);
        });
    }
    
    function showStatusAlert(isOnline, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${isOnline ? 'success' : 'danger'} alert-dismissible fade show bot-status-banner`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            <i class="fas fa-${isOnline ? 'check-circle' : 'exclamation-triangle'}"></i>
            <strong>${isOnline ? 'البوت متصل الآن' : 'تحذير: البوت غير متصل'}</strong>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // إزالة التنبيه تلقائياً بعد 10 ثواني
        setTimeout(() => {
            alertDiv.remove();
        }, 10000);
    }
    
    function updateStatusIndicator(isOnline) {
        const indicator = document.getElementById('bot-status-indicator');
        if (indicator) {
            indicator.className = `badge bg-${isOnline ? 'success' : 'danger'}`;
            indicator.innerHTML = `<i class="fas fa-circle"></i> ${isOnline ? 'متصل' : 'غير متصل'}`;
        }
    }
    
    // بدء المراقبة عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            checkBotStatus();
            setInterval(checkBotStatus, CHECK_INTERVAL);
        });
    } else {
        checkBotStatus();
        setInterval(checkBotStatus, CHECK_INTERVAL);
    }
})();
