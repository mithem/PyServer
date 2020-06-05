console_index = r"""<!DOCTYPE html>
<html lang="en-US">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>serverly admin console</title>
    <link rel="stylesheet" href="SUPERPATH/console/static/css/main.css"/>
    <style>
      .summaries  {
        display: flex;
      }
      .summary {
        padding: 10px;
        width: 97.5%;
        margin: 20px auto;
        border: none;
        border-radius: 8px;
        box-shadow: 0px 0px 6px #cccccc;
      }
       .summary > a {
        font-size: larger;
        font-weight: 600;
      }
      @media (prefers-color-scheme: dark){
        .summary {
          background-color: #333333;
          box-shadow: 0px 0px 6px #444444;
        }
      }
    </style>
    <script>
      function renewLogin(){
        var req = new XMLHttpRequest();
        req.open("POST", "SUPERPATH$_console_api_renew_login");
        req.send('please send WWW-Authenticate header!');
      }
      function updateUserSummary() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if (req.readyState === 4) {
            if (req.status !== 200) {
              console.error("Server response for users summary not ok:");
              console.error(req);
            }
            document.querySelector(
              ".summaries > .summary#summary-users > p"
            ).textContent = req.responseText;
          }
        };
        req.open("GET", "SUPERPATH$_console_summary_users");
        req.send(null);
      }
      function updateEndpointSummary() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if (req.readyState === 4) {
            if (req.status !== 200) {
              console.error("Server response for endpoint summary not ok:");
              console.error(req);
            }
            document.querySelector(
              ".summaries > .summary#summary-endpoints > p"
            ).textContent = req.responseText;
          }
        };
        req.open("GET", "SUPERPATH$_console_summary_endpoints");
        req.send(null);
      }
      function updateStatisticsSummary() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if (req.readyState === 4) {
            if (req.status !== 200) {
              handleResponse(req);
            }
            document.querySelector(
              ".summaries > .summary#summary-statistics > p"
            ).textContent = req.responseText;
          }
        };
        req.open("GET", "SUPERPATH$_console_summary_statistics");
        req.send(null);
      }
    </script>
  </head>
  <body>
    <nav>
      <a onclick="renewLogin()">serverly admin console</a>
    </nav>
    <div class="summaries">
      <div class="summary" id="summary-users">
        <a href="SUPERPATH$_console_users" class="mylink">users</a>
        <p>Loading...</p>
      </div>
      <div class="summary" id="summary-endpoints">
        <a href="SUPERPATH$_console_endpoints" class="mylink">endpoints</a>
        <p>Loading...</p>
      </div>
      <div class="summary" id="summary-statistics">
        <a href="SUPERPATH$_console_statistics" class="mylink">statistics</a>
        <p>Loading...</p>
      </div>
    </div>
  </body>
  <script>
    updateUserSummary();
    updateEndpointSummary();
    updateStatisticsSummary();
  </script>
</html>
"""

console_users = r"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>serverly admin console</title>
    <link rel="stylesheet" href="SUPERPATH/console/static/css/main.css">
    <style>
      /*
      .card {
        scrollbar-color: var(--scrollbar-thumb-color)
          var(--scrollbar-track-color);
      }
      */
      .tableContainer {
        height: 500px;
        overflow: scroll;
      }
      table {
        border-collapse: collapse;
      }
      table td,
      table th {
        border: 1px solid var(--table-border-color);
        background-color: var(--table-cell-background-color);
        text-align: left;
        padding: 8px;
      }
      table tr:nth-child(even) {
        background-color: var(--table-cell-highlight-color);
      }
    </style>
    <script src="SUPERPATH/console/static/js/main.js"></script>
    <script>
      function drawUsers(users) {
        let element = document.querySelector("table#users > tbody");
        element.innerHTML = "";
        for (let [attribute, value] of Object.entries(users[0])) {
          element.innerHTML += "<th>" + attribute + "</th>";
        }
        users.forEach((user) => {
          element.innerHTML += "<tr>";
          for (let [attribute, value] of Object.entries(user)) {
            console.debug(attribute + ":" + value);
            element.innerHTML += "<td>" + value + "</td>";
          }
          element.innerHTML += "</tr>";
        });
        console.info("refreshed users");
      }
      function selectMasterToggled(){
        let checked = document.querySelector("input#select-master").checked;
        var users = document.querySelectorAll("input.user-select");
        for(let user of users){
          user.checked = checked;
        }
      }
      function getIds(){
        var users = document.querySelectorAll("input.user-select");
        var ids = [];
        for(let user of users){
          if(user.checked){
            ids.push(parseInt(user.id.replace("user-", "")));
          }
        }
        return ids;
      }
      function change(){
        var ids = getIds();
        var url = "SUPERPATH$_console_change_or_create_user?ids=";
        for(id of ids){
          url += id + ",";
        }
        document.location.href = url;
      }
      function verify(){
        var ids = getIds();
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("POST", "SUPERPATH$_console_api_verify_users");
        req.send(JSON.stringify(ids));
      }
      function deverify(){
        var ids = getIds();
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("POST", "SUPERPATH$_console_api_deverify_users");
        req.send(JSON.stringify(ids));
      }
      function verimail() {
        var ids = getIds();
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("POST", "SUPERPATH$_console_api_verimail");
        req.send(JSON.stringify(ids));
      }
      function del(){
        var ids = getIds();
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("DELETE", "SUPERPATH$_console_api_delete_users");
        req.send(JSON.stringify(ids));
      }
      function resetPassword(){
        var ids = getIds();
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("DELETE", "SUPERPATH$_console_api_reset_password");
        req.send(JSON.stringify(ids));
      }
    </script>
  </head>
  <body>
    <nav>
      <a href="/console">serverly admin console</a>
    </nav>
    <div class="card">
      <span>actions</span>
      <div class="actions">
        <button class="action" id="change" onclick="change();">change/register</button>
        <button class="action" id="verify" onclick="verify();">verify</button>
        <button class="action" id="deverify" onclick="deverify();">deverify</button>
        <button class="action" id="verimail" onclick="verimail();">verimail</button>
        <button class="action" id="delete" onclick="del();">delete</button>
        <button class="action" id="resetPassword" onclick="resetPassword();">reset password</button>
      </div>
    </div>
    <div class="card">
      <span>users</span>
      <div class="tableContainer">
        $user_table
      </div>
    </div>
  </body>
  <script>
    document.querySelector("input#select-master").addEventListener("click", selectMasterToggled);
  </script>
</html>
"""

console_user_change_or_create = r"""<!DOCTYPE html>
<html lang="en-US">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>serverly admin console</title>
    <link rel="stylesheet" href="SUPERPATH/console/static/css/main.css" />
    <script src="SUPERPATH/console/static/js/main.js"></script>
    <style>
      #attributeContainer {
        display: grid;
        grid-template-columns: auto auto auto;
      }
      .field {
        text-align: right;
        margin: 4px;
        margin-right: 8px;
      }
      .field > input {
        margin: 4px;
        border-radius: 4px;
        border: none;
        background-color: #efefef;
        padding: 4px;
      }
      #progressbar {
        max-width: 300px;
        width: 80%;
        margin: 0px auto;
      }
      @media (prefers-color-scheme: dark){
        .card {
          background-color: #333333;
        }
      }
      .card {
        min-width: 400px;
        width: 100%;
        height: 600px;
      }
    </style>
  </head>
  <body>
    <nav>
      <a href="SUPERPATH$_console_index">serverly admin console</a>
    </nav>
    <div class="card" id="card">
      <span>change or register user</span>
      <div id="attributeContainer"></div>
      <progress id="progressbar" max="1" value="0">0/0</progress>
    </div>
  </body>
      <script>
      var userFinished = false;
      function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
      }
      function getCleanedValue(value){
        if (value.toLowerCase() == "true"){
          return true;
        }
        else if (value.toLowerCase() == "false"){
          return false;
        }
        else if (value === "" || value === "null"){
          return null;
        }
        var v = parseInt(value);
        if(!isNaN(v)){
          return v;
        }
        else {
        return value;
        }
      }
      function apply(){
        var user = {newPassword: undefined};
        const fields = document.querySelectorAll("#attributeContainer .field");
        for(field of fields){
          var attribute;
          var value;
          var attributeIsPassword = false;
          var attributeIsId = false;
          for(child of field.children){
            switch(child.className){
              case "attribute-name":
                if (child.textContent === "password"){ //requires special naming
                  attributeIsPassword = true;
                  continue;
                } else if (child.textContent === "id"){
                  attributeIsId = true;
                  continue;
                }
                attribute = child.textContent;
                break;
              case "attribute-value":
                if(attributeIsPassword){
                  user.newPassword = getCleanedValue(child.value);
                } else if(attributeIsId){
                  var i = getCleanedValue(child.value);
                  if (i === null){
                    i = getCleanedValue(child.placeholder);
                  }
                  user.id = i;
                }
                else if(child.value !== ""){
                  value = getCleanedValue(child.value);
                } else {
                  value = getCleanedValue(child.placeholder);
                }
                break;
              default:
                console.info("unimportant child of a field detected?!?!?");
            }
          }
          user[attribute] = value;
        }
        console.info(user);
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
          userFinished = true;
        }
        req.open("PUT", "SUPERPATH$_console_api_change_or_create_user");
        req.send(JSON.stringify(user));
      }
      function treatUser(user) {
        const container = document.getElementById("attributeContainer");
        const card = document.getElementById("card");
        container.innerHTML = "";
        card.removeChild(card.childNodes[card.childNodes.length - 1]);
        for(let [attribute, value] of Object.entries(user)){
          container.innerHTML += "<div class='field'><span class='attribute-name'>" + attribute + "</span><input class='attribute-value' type='text' placeholder='" + value + "'></input></div>";
        }
        document.getElementById("card").innerHTML += "<button id='apply'>apply</button>";
        document.querySelector("button#apply").addEventListener("click", apply);
      }
      function getUser(id, callback){
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if(req.readyState === 4){
            if (req.status === 200){
              callback(JSON.parse(req.responseText));
            }
          }
        }
        req.open("GET", "SUPERPATH$_console_api_get_user?id=" + id);
        const data = JSON.stringify({id: id});
        req.send(data);
      }
      async function main(){
        let ids = ${user_ids};
        const progressbar = document.getElementById("progressbar");
        progressbar.max = ids.length;
        for(var i = 0; i < ids.length; i++){
          userFinished = false;
          console.info("showing user…"),
          getUser(ids[i], treatUser);
          while(!userFinished){
            await sleep(1000);
          }
          progressbar.value = String.valueOf(parseInt(progressbar.value) + 1);
        }
        document.location.href = "SUPERPATH$_console_users";
      }
      main();
    </script>
</html>
"""

console_endpoints = r"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="/console/static/css/main.css" />
    <title>serverly admin console</title>
    <script src="/console/static/js/main.js"></script>
    <style>
      body {
        overflow-y: scroll;
      }
      .method-heading {
        font-size: 22px;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 2px;
      }
      .card {
        width: 100%;
        overflow-x: hidden;
      }
      table {
        width: 100%;
        margin: 5px;
        text-align: left;
        border-collapse: collapse;
      }
      table th {
        font-weight: 500;
        font-style: italic;
      }
      table tr:nth-child(even){
        background-color: var(--table-cell-highlight-color);
      }
      .tableContainer {
        height: 500px;
        overflow: scroll;
      }
      @media screen and (max-width: 750px){
        .card {
          overflow-x: scroll;
        }
      }
    </style>
    <script>
      function sortOnKeys(dict) {
        // https://stackoverflow.com/questions/10946880/sort-a-dictionary-or-whatever-key-value-data-structure-in-js-on-word-number-ke
        var sorted = [];
        for(var key in dict) {
            sorted[sorted.length] = key;
        }
        sorted.sort();

        var tempDict = {};
        for(var i = 0; i < sorted.length; i++) {
            tempDict[sorted[i]] = dict[sorted[i]];
        }

        return tempDict;
      }
      function newEndpoint(){
        let method = prompt("Method?");
        let path = prompt("Path?");
        let func = prompt("Function name (from your script)?");
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("POST", "SUPERPATH$_console_api_endpoint_new");
        req.send(JSON.stringify({method: method, path: path, function: func}))
      }
      function deleteEndpoint(){
        var endpoints = [];
        for(let methodcard of document.querySelectorAll(".card")){
          let method = methodcard.id.slice(5);
          for(let endpoint of document.querySelectorAll("#card-" + method + " tr")){
            var checked = endpoint.children[0].children[0].checked;
            try {
              var path = endpoint.children[1].children[0].textContent;
              if (checked){
                endpoints.push([method, path])
              }
            }
            catch { // headers don't have enough children}
            }
          }
        }
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("DELETE", "SUPERPATH$_console_api_endpoint_delete");
        req.send(JSON.stringify(endpoints));
      }
      function toggle(method){
        method = method.toLowerCase();
        let checkbox = document.querySelector("#card-" + method + " input.select-master");
        let checked = checkbox.checked;
        let endpoints = document.querySelectorAll("#card-" + method + " input.endpoint-select");
        for(var endpoint of endpoints){
          endpoint.checked = checked;
        }
      }
      function drawEndpoints(endpoints) {
        let endpointsContainer = document.getElementById("endpointsContainer");
        endpointsContainer.innerHTML = "";
        var result = "";
        for (let method of Object.keys(endpoints)) {
          result +=
            "<div class='card' id='card-" + method + "'><span class='method-heading'>" +
            method +
            "</span>";
          var table =
            "<table><thead><th><input type='checkbox' class='endpoint-select select-master' onclick=\"toggle('" + method + "')\"></input></th><th>path</th><th>function</th></thead><tbody>";
          for (let [path, funcname] of Object.entries(sortOnKeys(endpoints[method]))) {
            path = path.slice(1, -1)
            table +=
              "<tr><td><input type='checkbox' class='endpoint-select' id='endpoint-" + path + "'></input></td><td><a href='" +
              path +
              "' class='mylink'>" +
              path +
              "</a></td><td>" +
              funcname +
              "</td></tr>";
          }
          result += table + "</tbody></table></div>";
        }
        endpointsContainer.innerHTML = result;
      }
      function loadEndpoints() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if (req.readyState === 4) {
            if (req.status === 200) {
              drawEndpoints(JSON.parse(req.responseText));
            } else {
              handleResponse(req);
            }
          }
        };
        req.open("GET", "SUPERPATH$_console_api_endpoints_get");
        req.send(null);
      }
    </script>
  </head>
  <body>
    <nav>
      <a href="SUPERPATH$_console_index">serverly admin console</a>
    </nav>
    <div class="card">
      <span>actions</span>
      <div class="actions">
        <button onclick="newEndpoint()">new</button>
        <button onclick="deleteEndpoint()">delete</button>
      </div>
    </div>
    <div id="endpointsContainer"></div>
  </body>
  <script>
    loadEndpoints();
  </script>
</html>
"""

console_statistics = r"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="/console/static/css/main.css" />
    <title>serverly admin console</title>
    <script src="/console/static/js/main.js"></script>
    <style>
      body {
        overflow-y: scroll;
      }
      .method-heading {
        font-size: 22px;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 2px;
      }
      .card {
        width: 100%;
        overflow-x: hidden;
      }
      table {
        width: 100%;
        margin: 5px;
        text-align: left;
        border-collapse: collapse;
      }
      table th {
        font-weight: 500;
        font-style: italic;
      }
      table tr:nth-child(even){
        background-color: var(--table-cell-highlight-color);
      }
      .tableContainer {
        height: 500px;
        overflow: scroll;
      }
      @media screen and (max-width: 750px){
        .card {
          overflow-x: scroll;
        }
      }
    </style>
    <script>
      function sortOnKeys(dict) {
        // https://stackoverflow.com/questions/10946880/sort-a-dictionary-or-whatever-key-value-data-structure-in-js-on-word-number-ke
        var sorted = [];
        for(var key in dict) {
            sorted[sorted.length] = key;
        }
        sorted.sort();

        var tempDict = {};
        for(var i = 0; i < sorted.length; i++) {
            tempDict[sorted[i]] = dict[sorted[i]];
        }

        return tempDict;
      }
      function drawStatistics(stats) {
        let table = document.getElementById("statsTable");
        var result = "";
        for(let [func, data] of Object.entries(sortOnKeys(stats))){
          result += "<tr><td>" + func + "</td><td>" + data.mean.toFixed(3) + "</td><td>" + data.min.toFixed(3) + "</td><td>" + data.max.toFixed(3) + "</td><td>" + data.len + "</td></tr>";
        }
        table.innerHTML = result;
      }
      function loadStats() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          if (req.readyState === 4) {
            if (req.status === 200) {
              drawStatistics(JSON.parse(req.responseText));
            } else {
              handleResponse(req);
            }
          }
        };
        req.open("GET", "SUPERPATH$_console_api_statistics_get");
        req.send(null);
      }
      function resetStatistics() {
        var req = new XMLHttpRequest();
        req.onreadystatechange = () => {
          handleResponse(req);
        }
        req.open("DELETE", "SUPERPATH$_console_api_statistics_reset");
        req.send(null);
      }
    </script>
  </head>
  <body>
    <nav>
      <a href="SUPERPATH$_console_index">serverly admin console</a>
    </nav>
    <div class="card">
      <span>actions</span>
      <div class="actions">
        <button onclick="resetStatistics()">reset</button>
      </div>
    </div>
    <div class="card" id="statsContainer">
      <table>
        <thead>
          <tr>
            <th>function</th>
            <th>mean</th>
            <th>min</th>
            <th>max</th>
            <th>length</th>
          </tr>
        </thead>
        <tbody id="statsTable">
        </tbody>
      </table>
    </div>
  </body>
  <script>
    loadStats();
  </script>
</html>
"""

password_reset_page = r"""<!DOCTYPE html><html lang="en_US"><head><title>Reset password</title><script src="SUPERPATH/console/static/js/main.js"></script></head><body><script>var password = prompt("Your new password?");var req = new XMLHttpRequest();req.onreadystatechange= () => {if(req.readyState===4){handleResponse(req); if(req.status === 200){document.body.innerHTML = "<p>Password reset successful. You may now close this.</p>";}}}; req.open("POST", "SUPERPATH/api/resetpassword"); req.setRequestHeader("Authorization", "Bearer ${identifier}");req.send(JSON.stringify({password: password}));</script></body></html>"""

console_js_main = r"""function handleResponse(res){
  if(res.readyState === 4){
    alert("[" + res.status + "] " + res.responseText);
  }
}
"""

console_css_main = """body {
        background-color: #fafafa;
        overflow: hidden;
        font-family: "Poppins", "Sans-serif", "Times New Roman";
      }
      :root{
        --highlight-color: #23acf2;
        --table-border-color: #555555;
        --table-cell-highlight-color: #eeeeee;
        --table-cell-background-color: transparent;
      }
      nav {
        background-color: #ffffff;
        max-height: 8%;
        width: 100%;
        display: flex;
        border: none;
        border-radius: 10px;
        box-shadow: 0px 0px 10px #cccccc;
        margin-bottom: 10px;
      }
      nav a {
        font-weight: 600;
        font-size: 14pt;
        padding: 10px 20px;
        letter-spacing: 1px;
        margin: auto 0px;
        text-decoration: none;
        border-radius: 10px;
        color: black;
      }
      nav a:hover {
        padding: 8px 18px;
        border: 2px solid var(--highlight-color);
      }
      .card {
        margin: 10px auto auto auto;
        box-shadow: 0px 0px 10px #dddddd;
        border: none;
        border-radius: 12px;
        background-color: white;
      }
      .card > span {
        font-size: 26px;
        font-weight: 500;
        padding: 10px;
      }
      .actions button {
        margin: 10px;
      }
      .tableContainer {
        height: 500px;
        overflow: scroll;
      }
      *::-webkit-scrollbar {
        width: 4px;
      }
      *::-webkit-scrollbar-track {
        background: var(--scrollbar-track-color);
      }
      *::-webkit-scrollbar-thumb {
        background-color: var(--scrollbar-thumb-color);
        border: none;
        border-radius: 2px;
      }
      button {
        color: black;
      }
      .mylink {
        color: black;
        transition: .3s;
        text-decoration: none;
      }
      .mylink:hover {
        color: var(--highlight-color);
        transition: .2s;
      }
      @media (prefers-color-scheme: dark) {
        :root {
          --scrollbar-thumb-color: #555555;
          --scrollbar-track-color: #333333;
          --table-border-color: #777777;
          --table-cell-highlight-color: #555555;
        }
        * {
          color: white;
        }
        body {
          background-color: #111111;
        }
        nav {
          background-color: #333333;
          box-shadow: 0px 0px 10px #444444;
        }
        nav a {
          color: white;
        }
        .mylink {
          color: white;
        }
        .card {
          background-color: #333333;
          box-shadow: 0px 0px 10px #444444;
        }
      }
  """
