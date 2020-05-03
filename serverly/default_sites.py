from serverly.objects import Request, Response


def page_not_found_error(req: Request):
    return Response(404, body=f"<html><h3>404 - Page not found.</h3><br />Sorry, we couldn't find '{req.path.path}'.</html>")


def general_server_error(req):
    return Response(500, body=f"<html><h3>500 - Internal server error.</h3><br />Sorry, something went wrong on our side.")


def user_function_did_not_return_response_object(req):
    return Response(502, body=f"<html><h3>502 - Bad Gateway.</h3><br />Sorry, there is an error with the function serving this site. Please advise the server administrator that the function for '{req.path.path}' is not returning a response object.</html>")


console_index = """<!DOCTYPE html>
<html lang="en-US">
  <head>
    <title>serverly admin console</title>
    <style>
      body {
        display: flex;
        flex-direction: column;
        background-color: #fafafa;
        overflow: hidden;
        font-family: "Poppins", "Sans-serif", "Times New Roman";
      }
      nav {
        background-color: #ffffff;
        max-height: 8%;
        width: 100%;
        display: flex;
        border: none;
        border-radius: 10px;
        box-shadow: 0px 0px 10px #cccccc;
      }
      nav > a {
        font-weight: 600;
        font-size: 14pt;
        padding: 10px 20px;
        letter-spacing: 1px;
        margin: auto 0px;
        text-decoration: none;
        color: black;
      }
      nav > a:hover {
        padding: 8px 18px;
        border: 2px solid #23acf2;
        border-radius: 6px;
      }
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
      .summaries > .summary > a {
        font-size: larger;
        font-weight: 600;
        text-decoration: none;
        color: black;
        transition: 0.5s;
      }
      .summaries > .summary > a:hover {
        color: #23acf2;
        transition: 0.2s;
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
    </script>
  </head>
  <body>
    <nav>
      <a href="SUPERPATH$_console_index">serverly admin console</a>
    </nav>
    <div class="summaries">
      <div class="summary" id="summary-users">
        <a href="SUPERPATH$_console_users">users</a>
        <p>Loading...</p>
      </div>
    </div>
  </body>
  <script>
    updateUserSummary();
  </script>
</html>
"""

console_users = """<html><h1>Users overview!</h1></html>"""
