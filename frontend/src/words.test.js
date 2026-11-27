import { describe, expect, test } from "vitest";
import { amount, fraction, reminderText } from "./words.js";

const dose = { medicine_name: "Metformin", quantity: 0.5, food_timing: "after" };

describe("reminderText", () => {
  test("kannada uses everyday spoken words", () => {
    expect(reminderText("ಅಜ್ಜಿ", dose, "kn")).toBe(
      "ಅಜ್ಜಿ, ಮಾತ್ರೆ ತಗೊಳ್ಳೋ ಸಮಯ ಆಯ್ತು. ಊಟ ಆದ್ಮೇಲೆ Metformin, ಅರ್ಧ ಮಾತ್ರೆ ತಗೊಳ್ಳಿ.",
    );
  });

  test("hindi", () => {
    expect(reminderText("Nani", dose, "hi")).toBe(
      "Nani जी, दवा का समय हो गया है। खाने के बाद Metformin की आधी गोली ले लीजिए।",
    );
  });

  test("english", () => {
    expect(reminderText("Ajji", dose, "en")).toBe(
      "Ajji, it is time for your medicine. Please take half a tablet of Metformin after food.",
    );
  });

  test("numbers are said as words, and no food timing leaves no gap", () => {
    const two = { ...dose, quantity: 2, food_timing: "any" };
    expect(amount(2, "kn")).toBe("ಎರಡು");
    expect(reminderText("Ajji", two, "en")).toBe(
      "Ajji, it is time for your medicine. Please take two tablets of Metformin.",
    );
    expect(reminderText("ಅಜ್ಜಿ", two, "kn")).toBe(
      "ಅಜ್ಜಿ, ಮಾತ್ರೆ ತಗೊಳ್ಳೋ ಸಮಯ ಆಯ್ತು. Metformin, ಎರಡು ಮಾತ್ರೆ ತಗೊಳ್ಳಿ.",
    );
  });
});

test("fraction", () => {
  expect(fraction(0.5)).toBe("½");
  expect(fraction(1.5)).toBe("1½");
  expect(fraction(2)).toBe("2");
});
