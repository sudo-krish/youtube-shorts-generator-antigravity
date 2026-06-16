async function test() {
  const res = await fetch('http://localhost:8000/api/db/dump');
  const dbData = await res.json();
  const tables = Object.keys(dbData || {}).sort();
  for (const selectedTable of tables) {
    const currentData = selectedTable && dbData ? dbData[selectedTable] || [] : [];
    const columns = currentData.length > 0 ? Object.keys(currentData[0]) : [];
    
    currentData.forEach(row => {
      columns.forEach(col => {
         const val = row[col];
         let renderVal = val;
         if (val === null) renderVal = "null";
         else if (typeof val === 'number' && col.includes('time')) renderVal = "formatDate";
         else if (col === 'status') renderVal = "statusBadge";
         else if (typeof val === 'object') renderVal = JSON.stringify(val);
      });
    });
  }
  console.log("Success, no crashes in rendering logic.");
}
test().catch(console.error);
