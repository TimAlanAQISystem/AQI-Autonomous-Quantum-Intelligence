// SEGMENT ANALYTICS TEST SCRIPT
// Add this to your website's JavaScript file or in browser console for testing

// Wait for analytics to load
analytics.ready(function() {
    console.log('✅ Segment Analytics loaded successfully!');

    // Test basic tracking
    analytics.track('Test Event', {
        test_type: 'segment_installation',
        timestamp: new Date().toISOString(),
        page_url: window.location.href
    });

    console.log('✅ Test event sent to Segment');
});

// Test identify (replace with real user data)
analytics.identify('test_user_123', {
    name: 'Test User',
    email: 'test@scsdmcorp.com',
    company: 'Signature Corporation'
});

// Test page tracking
analytics.page('Test Page', {
    title: document.title,
    url: window.location.href,
    referrer: document.referrer
});

// Function to test custom events
function testSegmentEvent(eventName, properties) {
    analytics.track(eventName, properties);
    console.log('📊 Event sent:', eventName, properties);
}

// Example usage:
// testSegmentEvent('Button Click', { button_id: 'contact_form', page: 'home' });
// testSegmentEvent('Form Submit', { form_type: 'contact', fields_filled: 3 });

// Check if analytics object exists
if (typeof analytics !== 'undefined') {
    console.log('✅ Analytics object found');
    console.log('Available methods:', Object.keys(analytics));
} else {
    console.error('❌ Analytics object not found - check snippet installation');
}