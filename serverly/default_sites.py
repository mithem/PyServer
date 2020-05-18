from serverly.objects import Request, Response


def page_not_found_error(req: Request):
    return Response(404, body=f"<html><h3>404 - Page not found.</h3><br />Sorry, we couldn't find '{req.path.path}'.</html>")


def general_server_error(req):
    return Response(500, body=f"<html><h3>500 - Internal server error.</h3><br />Sorry, something went wrong on our side.")


def user_function_did_not_return_response_object(req):
    return Response(502, body=f"<html><h3>502 - Bad Gateway.</h3><br />Sorry, there is an error with the function serving this site. Please advise the server administrator that the function for '{req.path.path}' is not returning a response object.</html>")


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
    </script>
  </head>
  <body>
    <nav>
      <a href="SUPERPATH$_console_index">serverly admin console</a>
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
    </div>
  </body>
  <script>
    updateUserSummary();
    updateEndpointSummary();
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
      :root {
        --table-border-color: #555555;
        --table-cell-highlight-color: #eeeeee;
        --table-cell-background-color: transparent;
      }
      .topicContainer {
        background: white;
        box-shadow: 0px 0px 6px #cccccc;
        width: 95%;
        height: 90%;
        padding: 20px;
        margin: 30px auto 0px auto;
        border: none;
        border-radius: 12px;
        scrollbar-color: var(--scrollbar-thumb-color)
          var(--scrollbar-track-color);
      }
      .topicContainer > span {
        font-size: 26px;
        font-weight: 600;
      }
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
      @media (prefers-color-scheme: dark) {
        :root {
          --table-border-color: #777777;
          --table-cell-highlight-color: #555555;
          --table-cell-background-color: transparent;
        }
        .topicContainer {
          background-color: #3f3f3f;
          box-shadow: 0px 0px 6px #444444;
        }
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
    <div class="topicContainer">
      <span>Actions</span>
      <div class="actions">
        <button class="action" id="change" onclick="change();">change/register</button>
        <button class="action" id="verify" onclick="verify();">verify</button>
        <button class="action" id="deverify" onclick="deverify();">deverify</button>
        <button class="action" id="verimail" onclick="verimail();">verimail</button>
        <button class="action" id="delete" onclick="del();">delete</button>
        <button class="action" id="resetPassword" onclick="resetPassword();">reset password</button>
      </div>
    </div>
    <div class="topicContainer">
      <span>Users</span>
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
      .card {
        min-width: 400px;
        width: 100%;
        height: 600px;
        margin: auto;
        box-shadow: 0px 0px 10px #dddddd;
        border: none;
        border-radius: 12px;
        background-color: white;
      }
      .card > span {
        font-size: 26px;
        font-weight: 600;
        padding: 10px;
      }
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

password_reset_page = r"""<!DOCTYPE html><html lang="en_US"><head><title>Reset password</title><script src="SUPERPATH/console/static/js/main.js"></script></head><body><script>var password = prompt("Your new password?");var req = new XMLHttpRequest();req.onreadystatechange= () => {if(req.readyState===4){handleResponse(req); if(req.status === 200){document.body.innerHTML = "<p>Password reset successful. You may now close this.</p>";}}}; req.open("POST", "SUPERPATH/api/resetpassword"); req.setRequestHeader("Authorization", "Bearer ${identifier}");req.send(JSON.stringify({password: password}));</script></body></html>"""

console_js_main = r"""function handleResponse(res){
  if(res.readyState === 4){
    alert("[" + res.status + "] " + res.responseText);
  }
  function renewLogin(){
    var req = new XMLHttpRequest();
    req.open("GET", "SUPERPATH$_console_api_renew_login");
    req.send(null);
  }
}"""

console_css_main = """body {
        flex-direction: column;
        background-color: #fafafa;
        overflow: hidden;
        font-family: "Poppins", "Sans-serif", "Times New Roman";
      }
      :root{
        --highlight-color: #23acf2;
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
      }
  """
