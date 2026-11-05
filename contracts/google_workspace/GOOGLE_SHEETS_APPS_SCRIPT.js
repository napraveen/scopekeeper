/**
 * ScopeKeeper Google Sheets Apps Script Webhook
 * 
 * Instructions (Takes 60 seconds, 100% Free):
 * 1. Open Google Sheets (https://sheets.new)
 * 2. Click Extensions -> Apps Script
 * 3. Delete any code and paste this entire script
 * 4. Click Deploy -> New deployment
 * 5. Select type: 'Web app'
 *    - Description: 'ScopeKeeper Live Billing Relay'
 *    - Execute as: 'Me'
 *    - Who has access: 'Anyone'
 * 6. Click Deploy and copy the Web App URL!
 * 7. Set GOOGLE_SHEET_WEBHOOK_URL=<Your Web App URL> in ScopeKeeper .env
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Add header if sheet is brand new
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Timestamp", "CR ID", "Deliverable", "Client", 
        "Hours", "Rate ($)", "Total Value ($)", "Status", 
        "SOW Clause", "Amendment File", "GitHub PR URL"
      ]);
      sheet.getRange(1, 1, 1, 11).setFontWeight("bold").setBackground("#e0e7ff");
    }
    
    var data = JSON.parse(e.postData.contents);
    
    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.cr_id,
      data.deliverable,
      data.client || "Acme Corp",
      data.hours,
      data.rate || 90.0,
      data.total_value,
      data.status || "AUTHORIZED",
      data.clause || "Clause 6.1",
      data.amendment || "",
      data.pr_url || ""
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      row_added: data.cr_id
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
