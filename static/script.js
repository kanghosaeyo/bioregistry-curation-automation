const pmidInput = document.getElementById('pmid');
const extractBtn = document.getElementById('extract');
const statusEl = document.getElementById('status');
const outputArea = document.getElementById('output-area');
const jsonOutput = document.getElementById('json-output');
const copyBtn = document.getElementById('copy');
const copyMsg = document.getElementById('copy-msg');
const startOverBtn = document.getElementById('start-over');

function setStatus(msg){
  statusEl.textContent = msg;
}

function showOutput(){
  outputArea.classList.remove('hidden');
}

function hideOutput(){
  outputArea.classList.add('hidden');
}

function reset(){
  pmidInput.value = '';
  setStatus('');
  jsonOutput.value = '';
  hideOutput();
  copyMsg.textContent = '';
}

startOverBtn.addEventListener('click', (e)=>{ e.preventDefault(); reset(); });

extractBtn.addEventListener('click', async (e)=>{
  e.preventDefault();
  copyMsg.textContent = '';
  const pmid = pmidInput.value.trim();
  if(!/^[0-9]+$/.test(pmid)){
    setStatus('Please enter a numeric PMID (e.g., 12345678).');
    return;
  }

  setStatus('Extracting metadata...');
  hideOutput();
  try{
    const resp = await fetch('/extract', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({pmid})
    });

    if(!resp.ok){
      const err = await resp.json().catch(()=>({message: 'Unknown error'}));
      setStatus('Error: ' + (err.message || resp.statusText));
      return;
    }

    const body = await resp.json();
    if(body.status !== 'success'){
      setStatus('Error: ' + (body.message || 'Extraction failed'));
      return;
    }

    setStatus('Scraping database information...');
    // The backend performs scraping; show the result
    const formatted = JSON.stringify(body.data, null, 2);
    jsonOutput.value = formatted;
    showOutput();
    setStatus('Done. You can edit the JSON below.');
  }catch(err){
    setStatus('Unexpected error: ' + err.message);
  }
});

copyBtn.addEventListener('click', async ()=>{
  try{
    await navigator.clipboard.writeText(jsonOutput.value);
    copyMsg.textContent = 'Copied!';
    setTimeout(()=>copyMsg.textContent = '', 2000);
  }catch(e){
    copyMsg.textContent = 'Copy failed';
  }
});

// initialize
reset();
