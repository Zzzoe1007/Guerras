/* Bellum · mejoras de interacción sin dependencias externas */
(function () {
  "use strict";

  // Menú lateral en pantallas pequeñas.
  var botonMenu = document.querySelector("[data-menu-boton]");
  if (botonMenu) {
    botonMenu.addEventListener("click", function () {
      var abierto = document.body.classList.toggle("menu-abierto");
      botonMenu.setAttribute("aria-expanded", abierto ? "true" : "false");
    });
  }

  // Botones de impresión de los reportes.
  document.querySelectorAll("[data-imprimir]").forEach(function (enlace) {
    enlace.addEventListener("click", function (evento) {
      evento.preventDefault();
      window.print();
    });
  });

  // Atajo «/» para ir al buscador, como en las wikis.
  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "/" || evento.ctrlKey || evento.metaKey || evento.altKey) {
      return;
    }
    var activo = document.activeElement;
    var escribiendo =
      activo &&
      (activo.tagName === "INPUT" ||
        activo.tagName === "TEXTAREA" ||
        activo.tagName === "SELECT" ||
        activo.isContentEditable);
    if (escribiendo) {
      return;
    }
    var buscador = document.querySelector(".buscador input");
    if (buscador) {
      evento.preventDefault();
      buscador.focus();
      buscador.select();
    }
  });

  // Marca la pestaña activa según la ruta, si no venía definida.
  var ruta = window.location.pathname;
  document.querySelectorAll(".pestana").forEach(function (pestana) {
    var destino = pestana.getAttribute("href") || "";
    if (
      destino === ruta &&
      !pestana.classList.contains("pestana--activa") &&
      ruta !== "/"
    ) {
      pestana.classList.add("pestana--activa");
    }
  });
})();
