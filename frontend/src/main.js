import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/600.css";
import "./app.css";
import { mount } from "svelte";
import App from "./App.svelte";

mount(App, { target: document.getElementById("app") });
