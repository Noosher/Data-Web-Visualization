using Microsoft.AspNetCore.Mvc;

namespace DataWebApp.Controllers
{
    public class DatabaseController : Controller
    {
        public IActionResult Overview()
        {
            return View();
        }
    }
}
