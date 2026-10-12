import logoFull from "../assets/logo-full.png";

export default function LogoFull({ width = 220 }) {
  return (
    <img
      src={logoFull}
      width={width}
      alt="AI Finance Advisor"
      style={{ display: "block", height: "auto" }}
    />
  );
}
