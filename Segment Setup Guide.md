# SEGMENT ANALYTICS SETUP GUIDE

## For Signature Card Services Direct Merchant Center

### Step 1: Locate Your Website Files

Your website is at: <https://www.signaturecardservicesdirectmerchantcenter.com/>

You need to find the main HTML file (usually `index.html`) for your website. This could be:

- On your web hosting provider's file manager
- In your local development folder
- Through your website builder's editor

### Step 2: Add the Segment Snippet

1. Open your main HTML file
2. Find the `<head>` section (near the top)
3. Paste the following code **immediately after** the opening `<head>` tag:
2. Find the `<head>` section (near the top)
3. Paste the following code **immediately after** the opening `<head>` tag:

```html
<script>
  !function(){var i="analytics",analytics=window[i]=window[i]||[];if(!analytics.initialize)if(analytics.invoked)window.console&&console.error&&console.error("Segment snippet included twice.");else{analytics.invoked=!0;analytics.methods=["trackSubmit","trackClick","trackLink","trackForm","pageview","identify","reset","group","track","ready","alias","debug","page","screen","once","off","on","addSourceMiddleware","addIntegrationMiddleware","setAnonymousId","addDestinationMiddleware","register"];analytics.factory=function(e){return function(){if(window[i].initialized)return window[i][e].apply(window[i],arguments);var n=Array.prototype.slice.call(arguments);if(["track","screen","alias","group","page","identify"].indexOf(e)>-1){var c=document.querySelector("link[rel='canonical']");n.push({__t:"bpc",c:c&&c.getAttribute("href")||void 0,p:location.pathname,u:location.href,s:location.search,t:document.title,r:document.referrer})}n.unshift(e);analytics.push(n);return analytics}};for(var n=0;n<analytics.methods.length;n++){var key=analytics.methods[n];analytics[key]=analytics.factory(key)}analytics.load=function(key,n){var t=document.createElement("script");t.type="text/javascript";t.async=!0;t.setAttribute("data-global-segment-analytics-key",i);t.src="https://cdn.segment.com/analytics.js/v1/" + key + "/analytics.min.js";var r=document.getElementsByTagName("script")[0];r.parentNode.insertBefore(t,r);analytics._loadOptions=n};analytics._writeKey="XQPQgxDtecjoJvWOxgbg4AL4585aOdKo";;analytics.SNIPPET_VERSION="5.2.0";
  analytics.load("XQPQgxDtecjoJvWOxgbg4AL4585aOdKo");
  analytics.page();
  }}();
</script>
```

### Step 3: Verify Installation
After adding the snippet, save your changes and upload to your website. Then:

1. Visit your website: https://www.signaturecardservicesdirectmerchantcenter.com/
2. Open browser Developer Tools (F12)
3. Go to the Console tab
4. Look for any JavaScript errors
5. Check Network tab to see if `analytics.min.js` loads

### Step 4: Test Analytics Tracking
Once installed, you can test basic tracking:

```javascript
// Test pageview tracking (should happen automatically)
analytics.page();

// Test custom event tracking
analytics.track('Button Clicked', {
  button_name: 'contact_us',
  page: 'home'
});

// Test user identification
analytics.identify('user123', {
  name: 'John Doe',
  email: 'john@example.com'
});
```

### Step 5: Verify in Segment Dashboard
1. Go to your Segment workspace
2. Check the "Sources" section
3. Look for your JavaScript source
4. Check "Debugger" to see if events are coming through

### Important Notes:
- **Source ID**: The snippet uses write key `XQPQgxDtecjoJvWOxgbg4AL4585aOdKo`
- **Domain**: Make sure your canonical URL is set correctly: `https://www.signaturecardservicesdirectmerchantcenter.com/`
- **SSL Required**: Segment requires HTTPS for production websites
- **GDPR Compliance**: Consider adding consent management if required

### Troubleshooting:
- If you see "Segment snippet included twice" error, remove duplicate snippets
- If analytics don't load, check your internet connection and firewall
- If events don't appear in Segment, wait 5-10 minutes for processing

### Next Steps:
1. Install the snippet on your live website
2. Test basic pageview tracking
3. Set up custom event tracking for important user actions
4. Connect destinations (like Google Analytics, Facebook Pixel, etc.) in Segment

---

**Need help?** If you can't access your website files, contact your web hosting provider or website developer.