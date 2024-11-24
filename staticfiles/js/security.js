const Security = {
    escapeHTML: function(str) {
        if (!str) return str;
        return str.replace(/[&<>"']/g, function(match) {
            const escape = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            };
            return escape[match];
        });
    },
    
    sanitizeObject: function(obj) {
        if (typeof obj === 'string') {
            return this.escapeHTML(obj);
        }
        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObject(item));
        }
        if (typeof obj === 'object' && obj !== null) {
            const sanitized = {};
            for (let key in obj) {
                sanitized[key] = this.sanitizeObject(obj[key]);
            }
            return sanitized;
        }
        return obj;
    }
};