
document.addEventListener('copy', function(){
    chrome.storage.local.get("started", function(data){
        if (data.started == true)
        {
            var value = window.getSelection().toString();
            var link = location.href;
            writeToJSON(link, value);
        }
            
    });
});

function writeToJSON(url, text)
{
    chrome.storage.local.get("interactions", function(data){
        var interactions_list = data.interactions; 

        var json_file = {'url': url, 'text': text};
        var step = JSON.stringify(json_file).replace('\"','"');
        interactions_list.push(step);

        /* If the recording is STOPPED and the json_file is not empty, then save the json_file dictionary */
        chrome.storage.local.set({ "interactions": interactions_list });    
    });    
}




